"""
EPOS classes docstring

This module defines the EPOS class, that contains the observed exoplanets,
the survey detection efficiency, and the synthetic planet population.
see example.py for a simple demonstration of the class
"""

import numpy as np
import cgs
import EPOS.multi
from EPOS.plot.helpers import set_pyplot_defaults

class fitparameters:
	''' Holds the fit parameters. Usually initialized in epos.fitpars '''
	def __init__(self):
		self.fitpars={} # not in order
		self.keysall=[]
		self.keysfit=[]
		self.keys2d=[]
	
	def add(self, key, value, fixed=False, min=-np.inf, max=np.inf, 
				dx=None, text=None, is2D=False):
		'''Add a fit parameter
		
		Args:
			key(str): fit parameter dictionary key
			value(float): starting guess
			fixed(bool): keep this parameter fixed
			min(float): lower bound
			max(float): upper bound
			dx(float): initial dispersion for MCMC
			text(str): plot safe name?
			is2D(bool): use this parameter in the 2D parametric :meth:`EPOS.fitfunctions`
		'''
		fp=self.fitpars[key]= {}
		
		# list of keys
		self.keysall.append(key)
		if is2D: self.keys2d.append(key)
		if not fixed: self.keysfit.append(key)
		
		fp['key']= key
		fp['value_init']= value

		# T/F
		fp['fixed']=fixed
		
		# parameters for fitting
		if not fixed:
			fp['min']=min
			fp['max']=max
			# initial walker positions, can't be zero, default 10% or 0.1 dex
			dx=0.1*value if dx is None else dx
			fp['dx']=abs(dx) if (dx!=0) else 0.1

	def default(self, key, value, Verbose=True):
		if not key in self.keysall: 
			if Verbose: print '  Set {} to default {}'.format(key, value)
			self.add(key, value, fixed=True)
	
	def set(self, key, value):
		self.fitpars[key]['value_init']=value

	def setfit(self, mclist):
		for i,key in enumerate(self.keysfit):
			#self.fitpars[key]['value_fit']=mclist[self.keysfit.index(key)]
			self.fitpars[key]['value_fit']=mclist[i]
	
	def get(self, key, Init=False, attr=None):
		if attr is None:
			# return initial or fit value
			if Init or not 'value_fit' in self.fitpars[key]:
				return self.fitpars[key]['value_init']
			else:
				return self.fitpars[key]['value_fit']
		else:
			# list of attribute
			return self.fitpars[key][attr]
	
	def get2d(self, Init=False):
		# returns the values for the 2D distribution
		return [self.get(key, Init=Init) for key in self.keys2d]
	
	def getfit(self, Init=True, attr=None): 
		return [self.get(key, Init=Init, attr=attr) for key in self.keysfit]

	def getmc(self, key, parlist):
		# returns value for an mc run
		if self.fitpars[key]['fixed']:
			return self.fitpars[key]['value_init']
		else:
			return parlist[self.keysfit.index(key)]
			#try:				
			#except ValueError:
			#	raise ValueError('Parameter {} not defined'.format(key))

	def get2d_fromlist(self, parlist):
		# returns 2d from fit/fixed, fit supplied in list
		l2d= []
		for key in self.keys2d:
			if self.fitpars[key]['fixed']:
				l2d.append(self.fitpars[key]['value_init'])
				#pps= self.fitpars['pps']['value_init']
			else:
				l2d.append(parlist[self.keysfit.index(key)])
				#pps= parlist[self.keysfit.index('pps')]
		return l2d
	
	def checkbounds(self, parlist):
		for i, key in enumerate(self.keysfit):
			if parlist[i]<self.fitpars[key]['min']:
				raise ValueError('{} out of bounds, {} < {}'.format(
					key,parlist[i],self.fitpars[key]['min']))
			if parlist[i]>self.fitpars[key]['max']:
				raise ValueError('{} out of bounds, {} > {}'.format(
					key,parlist[i],self.fitpars[key]['max']))

class epos:
	"""The epos class
    
    Description:
    	Initialize

    Args:
    	name (str): name to use for directories
        RV(bool): Compare to radial velocity instead of transits
        Debug(bool): Log more output for debugging
        seed(int): Same random number for each simulation? True, None, or int
        Norm(bool): normalize pdf (deprecated?)
    
    Attributes:
		name(str): name
		plotdir(str): plot directory
		RV(bool): Compare to Radial Velocity instead of transit data
		Multi(bool): Do multi-planet statistics
		RandomPairing(bool): multis are randomly paired'''
Plots the exoplanet survey: observed planets and completeness
'''
		Isotropic(bool): Assume isotropic mutual inclinations
		Parametric(bool): parametric planet population?
		Debug(bool): Verbose logging
		seed(int): Random seed, int or None
    """
	def __init__(self, name, RV=False, Debug=False, seed=True, Norm=False):
		"""
		Initialize the class
		"""
		self.name=name
		self.plotdir='png/{}/'.format(name)
		self.RV= RV

		self.Multi=False
		self.RandomPairing= False
		self.Isotropic= False # phase out?
		
		#self.populationtype=None # ['parametric','model']
		#self.Parametric=None

		# Seed for the random number generator
		if seed is None: self.seed= None
		else:
			if type(seed) is int: self.seed= seed
			else: self.seed= np.random.randint(0, 4294967295)
			print '\nUsing random seed {}'.format(self.seed)
		
		self.Debug= False
		self.Parallel= True # speed up a few calculations 
		set_pyplot_defaults() # nicer plots

		# switches to be set later (undocumented)	
		self.Observation=False
		self.Range=False
		self.DetectionEfficiency=False
		self.Occurrence= False # inverse detection efficiency (?)
		self.Prep= False # ready to run? EPOS.run.once()
		self.MassRadius= False
		self.Radius= False # is this used?
		
		self.plotpars={} # dictionary to hold some customization keywords
		
	def set_observation(self, xvar, yvar, starID, nstars=1.6862e5):
		''' Observed planet population
		
		Args:
			xvar: planet orbital period [list]
			yvar: planet radius or M sin i [list]
			ID: planet ID [list]
			nstars: number of stars surveyed
		
		Note:
			Some pre-defined planet populations from Kepler can be generated from 
			:mod:`EPOS.kepler`
		'''
		order= np.lexsort((xvar,starID)) # sort by ID, then P
		self.obs_xvar=np.asarray(xvar)[order]
		self.obs_yvar=np.asarray(yvar)[order]
		self.obs_starID=np.asarray(starID)[order]
		self.nstars=nstars
		
		assert self.obs_xvar.ndim == self.obs_yvar.ndim == self.obs_starID.ndim == 1, 'only 1D arrays'
		assert self.obs_xvar.size == self.obs_yvar.size == self.obs_starID.size, 'arrays not same length'
	
		# set plot limits in observation 5% wider than data
		xmin,xmax= min(self.obs_xvar), max(self.obs_xvar)
		ymin,ymax= min(self.obs_yvar), max(self.obs_yvar)
		dx= (xmax/xmin)**0.05
		dy= (ymax/ymin)**0.05
		self.obs_xlim=[xmin/dx,xmax*dx]
		self.obs_ylim=[ymin/dy,ymax*dy]
		
		self.Observation=True
		
		# print some stuff
		print '\nObservations:\n  {} stars'.format(int(nstars))
		print '  {} planets'.format(self.obs_starID.size)
		EPOS.multi.indices(self.obs_starID, Verbose=True)
		epos.multi={}
		epos.multi['bin'], epos.multi['count']= \
			EPOS.multi.frequency(self.obs_starID, Verbose=True)
		epos.multi['pl cnt']= epos.multi['bin']* epos.multi['count']
		epos.multi['Pratio'], epos.multi['Pinner']= \
			EPOS.multi.periodratio(self.obs_starID, self.obs_xvar, Verbose=True)
		epos.multi['cdf']= EPOS.multi.cdf(self.obs_starID, Verbose=True)	
		
	def set_survey(self, xvar, yvar, eff_2D, Rstar=1.0, Mstar=1.0):
		'''Survey detection efficiency (completeness)
		Args:
			xvar: planet orbital period grid [list]'
			yvar: planet radius or M sin i grid [list]
			eff_2D: 2D matrix of detection efficiency
			Rstar: stellar radius, for calculating transit probability
			Mstar: stellar mass, for period-semimajor axis conversion
		
		Note:
			Some pre-defined detection efficiencies from Kepler can be generated from 
			:mod:`EPOS.kepler`
		'''
		self.eff_xvar=np.asarray(xvar)
		self.eff_yvar=np.asarray(yvar)
		self.eff_2D=np.asarray(eff_2D)
		
		assert self.eff_xvar.ndim == self.eff_yvar.ndim == 1, 'only 1D arrays'
		assert self.eff_2D.ndim == 2, 'Detection efficiency must by a 2dim array'
		if self.eff_2D.shape != (self.eff_xvar.size, self.eff_yvar.size):
			raise ValueError('Mismatching detection efficiency'
			'\n: nx={}, ny={}, (nx,ny)=({},{})'.format(self.eff_xvar.size, self.eff_yvar.size, *self.eff_2D.shape))
	
		self.eff_xlim= [min(self.eff_xvar),max(self.eff_xvar)]
		self.eff_ylim= [min(self.eff_yvar),max(self.eff_yvar)]
		
		self.Mstar= Mstar
		if self.RV:
			self.completeness= self.eff_2D
		else:
			self.Rstar=Rstar # Solar radii
			self.Pindex= -2./3.
			fourpi2_GM= 4.*np.pi**2. / (cgs.G*self.Mstar*cgs.Msun)
			self.fgeo_prefac= self.Rstar*cgs.Rsun * fourpi2_GM**(1./3.) / cgs.day**(2./3.)
			#print self.fgeo_prefac
			P, R= np.meshgrid(self.eff_xvar, self.eff_yvar, indexing='ij')
			self.completeness= self.eff_2D * self.fgeo_prefac*P**self.Pindex

		self.DetectionEfficiency=True
	
	def set_ranges(self, xtrim=None, ytrim=None, xzoom=None, yzoom=None, 
			LogArea=False, Occ=False):
		
		if self.Range: raise ValueError('Range already defined')
		if not self.Observation: raise ValueError('No observation defined')
		if not self.DetectionEfficiency: raise ValueError('No detection effifiency defined')
		
		''' Define the region where completeness is calculated'''
		if xtrim is None:
			print 'Trimming x-axis from detection efficiency'
			self.xtrim= self.eff_xlim
		else:
			self.xtrim= [max(xtrim[0], self.eff_xlim[0]), min(xtrim[1], self.eff_xlim[1])]

		if ytrim is None:
			print 'Trimming y-axis from detection efficiency'
			self.ytrim= self.eff_ylim
		else:
			self.ytrim= [max(ytrim[0], self.eff_ylim[0]), min(ytrim[1], self.eff_ylim[1])]
		
		''' Define a smaller region where observational comparison is performed'''	
		if xzoom is None:
			print 'Not zooming in on x-axis for model comparison'
			self.xzoom= self.xtrim
		else:
			self.xzoom= [max(xzoom[0], self.xtrim[0]), min(xzoom[1], self.xtrim[1])]

		if yzoom is None:
			print 'Not zooming in on y-axis for model comparison'
			self.yzoom= self.ytrim
		else:
			self.yzoom= [max(yzoom[0], self.ytrim[0]), min(yzoom[1], self.ytrim[1])]
		
		if (xzoom is None) and (yzoom is None):
			self.Zoom=False
		elif (self.xzoom==self.xtrim) and (self.yzoom==self.ytrim):
			self.Zoom=False
			print 'Not a zoom'
		else:
			self.Zoom=True
		
		''' Prep the grid for the observable'''
		# make sure range _encompasses_ trim
		ixmin,ixmax= _trimarray(self.eff_xvar, self.xtrim)
		iymin,iymax= _trimarray(self.eff_yvar, self.ytrim)
	
		self.MC_xvar= self.eff_xvar[ixmin:ixmax]
		self.MC_yvar= self.eff_yvar[iymin:iymax]
		self.MC_eff= self.eff_2D[ixmin:ixmax,iymin:iymax]
		
		# scale factor to multiply pdf such that occurrence in units of dlnR dlnP
		if LogArea:
			area= np.log10
			self.plotpars['area']= 'd log'
		else:
			area= np.log
			self.plotpars['area']= 'd ln'

		self.scale_x= self.MC_xvar.size/area(self.MC_xvar[-1]/self.MC_xvar[0])
		self.scale_y= self.MC_yvar.size/area(self.MC_yvar[-1]/self.MC_yvar[0])
		self.scale= self.scale_x * self.scale_y
		
		self.X, self.Y= np.meshgrid(self.MC_xvar, self.MC_yvar, indexing='ij')
		
		''' Prep the grid for the PDF, if using a mass-radius conversion'''
		if self.PDF:
			if self.MassRadius:
				self.in_ytrim= self.masslimits
				self.in_yvar= np.logspace(*np.log10(self.in_ytrim))
				self.scale_in_y= \
					self.in_yvar.size/area(self.in_yvar[-1]/self.in_yvar[0])	
				self.scale_in= self.scale_x * self.scale_in_y
				self.X_in,self.Y_in= np.meshgrid(self.MC_xvar,self.in_yvar,indexing='ij')
			else:
				self.in_ytrim= self.ytrim
				self.in_yvar= self.MC_yvar
				self.scale_in_y= self.scale_y 
				self.scale_in= self.scale
				self.X_in, self.Y_in= self.X, self.Y
			
		''' plot ticks '''
		if self.RV:
			self.xticks= [1,10,100]
			self.yticks= [1,10,100,1000]
		else:
			self.xticks= [1,10,100,1000]
			self.yticks= [0.5,1,2, 4,10]
			
		self.Range=True
		
		if Occ:
			if self.MassRadius:
				raise ValuError('Plotting occurrence with mass-radius not yet supported')
				#pass
				
			if not hasattr(self,'occurrence'):
				self.occurrence={}
			focc= self.occurrence			
	
			focc['xzoom']={}
			#ygrid= np.exp(np.arange(np.log(self.MC_yvar[0]),np.log(self.MC_yvar[-1])+0))
			ygrid= self.MC_yvar
			focc['xzoom']['x']= [self.xzoom]* (ygrid.size-1)
			focc['xzoom']['y']= [[i,j] for i,j in zip(ygrid[:-1],ygrid[1:])]

			focc['yzoom']={}
			#xgrid= np.exp(np.arange(np.log(self.MC_xvar[0]),np.log(self.MC_xvar[-1])+0))
			xgrid= self.MC_xvar
			focc['yzoom']['x']= [[i,j] for i,j in zip(xgrid[:-1],xgrid[1:])]
			focc['yzoom']['y']= [self.yzoom]* (xgrid.size-1)
			
	def set_bins(self, xbins=[[1,10]], ybins=[[1,10]],xgrid=None, ygrid=None,Grid=False):
		'''
		Initialize period-radius (or mass) bins for occurrence rate calculations
		
		Description:
    		Bins can be generated from a grid, f.e. xgrid=[1,10,100], 
    		or from a list of bin edges, f.e. xbins= [[1,10],[10,100]]
    	
    	Args:
    		xbins(list):	(list of) period bin edges
    		ybins(list):	(list of) radius/mass bin edges
    		xgrid(list):	period bin in interfaces
    		ygrid(list):	radius/mas bin interfaces
    		Grid(bool):
    			If true, create a 2D grid from bins: nbins = nx ``*`` ny.
    			If false, pair x and y bins: nbins == nx == ny
		'''
		if not hasattr(self,'occurrence'):
			self.occurrence={}
		focc= self.occurrence
		
		#generate list of bin inner and outer edges
		if xgrid is None:
			if np.ndim(xbins) ==1:
				assert len(xbins)==2
				_xbins= [xbins]
			elif np.ndim(xbins) ==2: 
				_xbins= xbins
			else:
				raise ValueError('wrong bin dimensions')
		else:
			_xbins= np.array([[i,j] for i,j in zip(xgrid[:-1],xgrid[1:])])

		if ygrid is None:
			if np.ndim(ybins) ==1:
				assert len(ybins)==2
				_ybins= [ybins]
			elif np.ndim(ybins) ==2: 
				_ybins= ybins
			else:
				raise ValueError('wrong bin dimensions')
		else:
			_ybins= np.array([[i,j] for i,j in zip(ygrid[:-1],ygrid[1:])])
		
		focc['bin']={}
		if Grid:
			focc['bin']['x']= np.tile(_xbins, (len(_ybins),1))
			focc['bin']['y in']= np.tile(_ybins, (len(_xbins),1))
			# TODO: store 1d -> 2d mapping
			
		else:		
			if np.shape(_xbins) != np.shape(_ybins):
				raise ValueError('unequal amount of bins. Use Grid=True?')
			focc['bin']['x']= _xbins
			focc['bin']['y in']= _ybins
		
	def set_parametric(self, func):
		'''Define a parametric function to generate the planet size-period distribution
		
		Description:
			Function should be callable as func(X, Y, \*fitpars2d) with
			X(np.array): period
			Y(np.array): size (radius or mass)
			The list of fit parameters fitpars2d will be constructed from parameters 
			added using :func:`EPOS.fitparameters.add` with is2D=True
			
		Note:
			Some pre-defined functions can be found in :mod:`EPOS.fitfunctions`
		
		Args:
			func (function): callable function
		
		'''		
		if not callable(func): raise ValueError('func is not a callable function')		
		self.func=func
		
		self.pdfpars= fitparameters()
		
		self.Parametric= True
		self.PDF=True	
		self.fitpars=self.pdfpars
		
	def set_multi(self, spacing=None):
		if not self.Parametric:
			raise ValueError('Define a parametric planet population first')
		self.Multi=True
		
		self.RandomPairing= (spacing==None)
		self.spacing= spacing # None, brokenpowerlaw, dimensionless
	
	def set_population(self, name, sma, mass, 
					inc=None, starID=None, tag=None, Verbose=False):
		# tag is fit parameter, i.e. metallicity, surface density, or model #

		if hasattr(self, 'pfm'):
			raise ValueError('expand: adding multiple populations?')
		
		self.Parametric=False
		self.modelpars= fitparameters()
		self.fitpars= self.modelpars
		
		# length checks
		try:
			if len(sma) != len(mass): 
				raise ValueError('sma ({}) and mass ({}) not same length'.format(len(sma),len(mass)))
		except: 
			raise ValueError('sma ({}) and mass ({}) have to be iterable'.format(type(sma), type(mass)))
		
		# model has mutual inclinations?
		self.Multi= (inc != None)
		
		pfm= self.pfm= {}
		pfm['name']= name
		
		# lexsort?
		pfm['sma']= np.asarray(sma)
		pfm['M']= np.asarray(mass)
		pfm['ID']= np.arange(len(sma)) if starID is None else np.asarray(starID)
		if tag is not None:
			pfm['tag']= np.asarray(tag)		
		if inc is None:
			self.Multi=False
		else:
			self.Multi= True
			pfm['inc']= np.asarray(inc)
		
		pfm['P']= pfm['sma']**1.5 * 365.25 # update
		#pfm['dP']= ??
		
		pfm['np']= pfm['ID'].size
		pfm['ns']= np.unique(pfm['ID']).size

		''' If multiple planets per stars: Lexsort, period ratio'''
		if pfm['np'] > pfm['ns']:
			order= np.lexsort((pfm['sma'],pfm['ID'])) # sort by ID, then sma
			for key in ['ID','sma','M','P','inc','tag']:
				if key in pfm: pfm[key]=pfm[key][order]
			
			EPOS.multi.indices(pfm['ID'], Verbose=True)
			EPOS.multi.frequency(pfm['ID'], Verbose=True)
			
			single, multi, ksys, multis= EPOS.multi.nth_planet(pfm['ID'],pfm['P'])
			pfm['dP']=np.ones_like(pfm['P'])
			pfm['dP'][single]= 0 #np.nan
			for km in multis[1:]:
				# 2nd, 3rd, 4th??
				pfm['dP'][km]= pfm['P'][km]/pfm['P'][np.array(km)-1]
# 			print pfm['ID'][1:6]
# 			print pfm['P'][1:6]
# 			print pfm['dP'] # not ok?

		pfm['M limits']=[np.min(pfm['M']),np.max(pfm['M'])]
		pfm['P limits']=[np.min(pfm['P']),np.max(pfm['P'])]
		
		# set plot limits in model 5% wider than data
		xmin,xmax= min(pfm['P']), max(pfm['P'])
		ymin,ymax= min(pfm['M']), max(pfm['M'])
		dx= (xmax/xmin)**0.05
		dy= (ymax/ymin)**0.05
		self.mod_xlim=[xmin/dx, xmax*dx]
		self.mod_ylim=[ymin/dy, ymax*dy]
# 		self.mod_xlim=[min(xmin/dx, self.mod_xlim[0]),max(xmax*dx, self.mod_xlim[1])]
# 		self.mod_ylim=[min(ymin/dy, self.mod_ylim[0]),max(ymax*dy, self.mod_ylim[1])]
		
	
	def set_massradius(self, MR, name, masslimits= [0.01,1e3]):
		print '\nMass-Radius relation from {}'.format(name)
		if self.MassRadius:
			raise ValueError('Already defined a Mass-Radius conversion function ')
		# actually radius as funtion of mass (mass-to-radius)
		if not callable(MR): raise ValueError('Mass-Radius function is not callable')

		self.MassRadius=True
		self.MR=MR
		self.MR_label=name
		
		self.masslimits=masslimits 
		meanradius= MR(masslimits)[0]
		print 'Mass and Radius limits:'
		print '  min M = {:.3f}-> <R> ={:.2f}'.format(masslimits[0], meanradius[0] )
		print '  max M = {:.0f}-> <R> ={:.1f}'.format(masslimits[-1], meanradius[-1] )
		

def _trimarray(array,trim):
	# trims array of points not needed for interpolation
	if trim[0] < array[1]:
		imin=0
	else:
		imin = np.searchsorted(array, trim[0], side='left')-1
	
	if trim[1] > array[-2]:
		imax=len(array)
	else:
		imax = np.searchsorted(array, trim[1], side='left')+1
	
	return imin, imax
