''' 
This module contains helper functions to load kepler survey data into EPOS
'''
import numpy as np
import os
import EPOS

try:
	from astropy.table import Table
except ImportError:
	print '\nWarning: Could not import astropy.table'

fpath= os.path.dirname(EPOS.__file__)

def dr25(subsample='all', score=0.9, Gaia=False, Huber=True, Vetting=False):
	'''
	Generates Kepler DR25 planet population and detection efficiency
	
	Args:
		subsample(str):	Subsample, choose from 'all', 'M', 'K', 'G', or 'F'
		score(float): Disposition score, 0-1, default 0.9
		Gaia(bool): Use Gaia data (Stellar radii from Berger+ 2018)
		Huber(bool): Use logg cut from Huber+ 2016
		Vetting(bool): include vetting completeness
		
	Returns:
		tuple: two dictionaries
		
		obs(dict):
			xvar(np.array of float): orbital period
			yvar(np.array of float): planet radius
			starID(np.array): stellar ID
			nstars(int): number of stars surveyed
		survey(dict):
			the grid is in xvar,yvar, the detection efficiency in eff_2D 
	'''
	if not os.path.isdir('temp/'): os.makedirs('temp/')

	if Gaia:
		#fkoi= 'temp/q1_q17_dr25-gaia-r1_koi.npz'
		fkoi= 'temp/q1_q17_dr25-gaia-r2_koi.npz'
	else:
		fkoi= 'temp/q1_q17_dr25_koi.npz'
		
	if os.path.isfile(fkoi):
		print '\nLoading planets from {}'.format(fkoi)
		koi= np.load(fkoi)
	else:
		print '\nReading planet candidates from IPAC file' 
		try:
			ipac=Table.read(fpath+'/files/q1_q17_dr25_koi.tbl',format='ipac')
		except NameError:
			raise ImportError('You need to install astropy for this step')
		#print ipac.keys()
		nonzero= (ipac['koi_srad']>0)
		nremove= ipac['koi_srad'].size- ipac['koi_srad'][nonzero].size
		print '  removed {} planets with no stellar radii'.format(nremove)
		koi= {key: np.array(ipac[key][nonzero]) for key in 
				['kepid','koi_prad','koi_period',
				'koi_steff', 'koi_slogg', 'koi_srad', 'koi_depth',
				'koi_pdisposition','koi_score'] }
		# isnan= ~(koi['koi_srad']>0)
		# print isnan.size
		# print koi['kepid'][isnan]
		# print koi['koi_srad'][isnan]
		# print koi['koi_pdisposition'][isnan]
		# print koi['koi_prad'][isnan]

		if Gaia:
			# Stellar radius table from Berger+ in prep., revision 2
			#fgaia= 'files/DR2PapTable1_v1.txt'
			fgaia= '{}/files/DR2PapTable1.txt'.format(fpath)
			a=np.loadtxt(fgaia, delimiter='&', unpack=True, skiprows=1, comments='\\')
			
			# sort stars by ID for easy matching
			order= a[0].argsort()
			a= a[:,order]
			assert np.all(np.sort(a[0])==a[0]), 'Whoops II'
			
			common= np.intersect1d(koi['kepid'], a[0], assume_unique=False)
			print '  {} common out {} kois and {} stars in gaia'.format(common.size, 
							koi['kepid'].size, a[0].size)
			
			# remove kois w/ no gaia data
			koi_in_gaia= np.in1d(koi['kepid'], a[0])
			for key in koi:
				koi[key]= koi[key][koi_in_gaia]
			print '  {} stars, {} kois in gaia'.format(koi['kepid'].size, 
				np.unique(koi['kepid']).size)
			
			# remove gaia data w/ no koi
			gaia_in_koi= np.in1d(a[0], koi['kepid'])
			gaia=dict(starID= a[0][gaia_in_koi],
					  Teff=a[2][gaia_in_koi],
					  distance=a[4][gaia_in_koi],
					  Rst= a[7][gaia_in_koi],
					  giantflag= a[11][gaia_in_koi])
			print '  {} gaia stars that are kois'.format(gaia['starID'].size)
			assert gaia['starID'].size == np.unique(koi['kepid']).size
			
			# stars w/ multiple planet candidates		
			_, st_to_pl= np.unique(koi['kepid'], return_inverse=True)
			assert np.all(gaia['starID'][st_to_pl]==koi['kepid'])
			
			# update radii
			with np.errstate(divide='ignore'):
				increase= np.nanmedian(gaia['Rst'][st_to_pl]/ koi['koi_srad'])-1.
			print '  KOI radii increased by {:.1%}'.format(increase)
			
			koi['koi_steff']= gaia['Teff'][st_to_pl]
			with np.errstate(divide='ignore', invalid='ignore'):
				koi['koi_prad']*= gaia['Rst'][st_to_pl]/ koi['koi_srad']
			koi['distance']= gaia['distance'][st_to_pl]
			koi['giantflag']= gaia['giantflag'][st_to_pl]

			#print np.nanmedian((koi['koi_srad']*koi['koi_depth']**0.5)/ koi['koi_prad'])
		
		np.savez(fkoi, **koi)

	''' Remove giant stars'''
	if Gaia:
		isdwarf= koi['giantflag'] == 0
		suffix='gaia-r1' # completeness needs update to r2
	elif Huber:
		isdwarf= koi['koi_slogg'] > 1./4.671 * \
					np.arctan((koi['koi_steff']-6300.)/-67.172)+ 3.876
		isgiant= koi['koi_slogg'] < np.where(koi['koi_steff']>5000, 
									13.463-0.00191*koi['koi_steff'],3.9)
		issubgiant= ~isdwarf & ~isgiant
		suffix='huber'
	else:
		isdwarf= koi['koi_slogg']>4.2
		suffix='logg42'
	
	''' Select reliable candidates '''
	iscandidate= koi['koi_pdisposition']=='CANDIDATE'
	isreliable= koi['koi_score']>=score # removes rolling band, ~ 500 planets
	print '  {}/{} dwarfs'.format(isdwarf.sum(), isdwarf.size)
	print '  {} candidates, {} false positives'.format((isdwarf&iscandidate).sum(), 
				(isdwarf&~iscandidate).sum() )
	print '  {}+{} with score > {:.2f}'.format((isdwarf&iscandidate&isreliable).sum(), 
				(isdwarf&~iscandidate&isreliable).sum(),score )

	if score >= 0.5:
		isall= isdwarf & isreliable # reliability score cuts out false positives
	else:
		isall= isdwarf & iscandidate & isreliable

	''' Select a spectral type sub-smaple'''
	if subsample=='all':
		slice=isall
	elif subsample in ['M','K','G','F']:
		Teff={'M':[2400, 3865], 'K':[3865, 5310], 'G':[5310, 5980], 'F':[5980, 7320]}
		slice= isall & (Teff[subsample][0]<koi['koi_steff']) \
						& (koi['koi_steff']<=Teff[subsample][1])
	elif subsample[0] == 'T':
		Tmin=int(subsample[1:])-250
		Tmax=int(subsample[1:])+250
		slice= isall & (Tmin<koi['koi_steff']) & (koi['koi_steff']<=Tmax)
	else:
		raise ValueError('Subsample {} not recognized'.format(subsample))
	#if Huber: slice['subgiants']=issubgiant
	
	obs= {'xvar':koi['koi_period'][slice],
		'yvar':koi['koi_prad'][slice], 
		'starID':koi['kepid'][slice]}
	
	''' Load pre-calculated detection efficiencies '''
	# from dr25_epos.py
	sfile= 'dwarfs' if subsample=='all' else subsample
	eff= np.load('{}/files/completeness.dr25.{}.{}.npz'.format(fpath,sfile, suffix))
	#eff= np.load('files/det_eff.dr25.{}.npz'.format(subsample))
	survey= {'xvar':eff['P'], 'yvar':eff['Rp'], 'eff_2D':eff['fsnr'], 
			'Mstar': eff['Mst'], 'Rstar':eff['Rst']}
	obs['nstars']= eff['n']
  	
	''' Add vetting completeness '''
	if Vetting:
		if subsample=='all' and score == 0.9:
			X,Y= np.meshgrid(eff['P'], eff['Rp'], indexing='ij')
			#vet_2D= fbpl2d( (X,Y), 0.9, 46., -0.053, -0.37, 5.6, 0.19, -2.3)
			if Gaia:
				vetpars= 0.84, 55., -0.07, -0.37, 8.2, 0.13, 0.13
			else:
				vetpars= 0.88, 53., -0.07, -0.39, 5.7, 0.19, 0.19
				
			vet_2D= fbpl2d( (X,Y), *vetpars)
			survey['vet_2D']= vet_2D
			assert vet_2D.shape == eff['fsnr'].shape
		else:
			print 'no vetting completeness for {} with score={}'.format(subsample, score)
	
	return obs, survey
	
def fbpl2d((x,y), a, b, c, d, e, f, g):
	bpl= a* (x/b)**np.where(x<b, c, d) * (y/e)**np.where(y<e, f,g)
	return np.maximum(0.2, np.minimum(bpl, 1.))

'''
NOTE: Kepler files from Q16-epos.py
cp ~/Kepler/npz/completeness.Q16.epos.*.npz EPOS/files/
cp ~/Kepler/npz/KOI.Q16.epos.*.npz EPOS/files/

#cp ~/Kepler/npdict/Q16.occ.Rp-P.sptype.*.npdict EPOS/files/
'''

def obs_Q16(subsample='all'):
	'''
	returns the Q16 exoplanet catalogue as numpy arrays
	
	Returns:
		P(np.array):   Orbital period in days
		Rp(np.array):  Planet radius in earth radii'
		KID(np.array): star identifier (for multis)'
	'''
	KOI= np.load('files/KOI.Q16.epos.{}.npz'.format(subsample))
	return KOI['P'], KOI['Rp'], KOI['KID']

def eff_Q16(subsample='all'):
	'''
	returns the Q16 survey detection efficiency as a 2D matrix
	
	Returns:
		P(np.array):   Orbital period in days
		Rp(np.array):  Planet radius in earth radii'
		eff(np.array):2D matrix of detection efficiency [0-1]
	'''
	eff= np.load('{}/files/completeness.Q16.epos.{}.npz'.format(fpath,subsample))
	return eff['x'], eff['y'], eff['fsnr']
