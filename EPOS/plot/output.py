import numpy as np
import matplotlib.pyplot as plt
import periodradius, massradius, multi, helpers

clrs= ['r','g','b','m'] # in epos.prep
fmt_symbol= {'ls':'', 'marker':'o', 'mew':2, 'ms':8,'alpha':0.6}

''' output '''
def all(epos):

	if hasattr(epos, 'synthetic_survey'):
		print '\nPlotting output...'
	
		if epos.MonteCarlo:
			periodradius.periodradius(epos, Parametric=epos.Parametric, SNR=False)
			periodradius.periodradius(epos, Parametric=epos.Parametric, SNR=True)
		else:
			# plot period-radius for non-MC
			pass
		
		periodradius.cdf(epos)
		periodradius.panels(epos)
	
		if epos.Multi:
			multi.periodradius(epos)
			multi.periodradius(epos, Nth=True)
	
			multi.multiplicity(epos, MC=True)
			multi.multiplicity(epos, MC=True, Planets=True)
			multi.multiplicity_cdf(epos, MC=True)
			multi.periodratio(epos, MC=True)
			if epos.Parametric and epos.spacing is not None:
				multi.periodratio(epos, MC=True, Input=True)
			multi.periodratio_cdf(epos, MC=True)
			multi.periodinner(epos, MC=True)
			if epos.Parametric and epos.spacing is not None:
				multi.periodinner(epos, MC=True, Input=True)
			multi.periodinner_cdf(epos, MC=True)
			# pdf per subgroup
			#periodradius.pdf(epos)
			#periodradius.pdf_3d(epos)

		if epos.MassRadius:
			massradius.massradius(epos, MC=True)
			massradius.massradius(epos, MC=True, Log=True)

		else:
			if epos.Parametric and epos.Multi and not epos.RV:
				multi.periodratio(epos, MC=True, N=True)
				if epos.spacing is not None:
					multi.periodratio(epos, MC=True, N=True, Input=True)
				multi.periodinner(epos, MC=True, N=True)

	else:
		print '\nNo output to plot, did you run EPOS.run.once()? \n'

		
def out_Pratio(epos, SNR=True, Parametric=False):

	if SNR:
		sim=epos.synthetic_survey
		suffix=''
		fsuffix=''
	else:
		sim=epos.transit
		suffix=' (no SNR)'
		fsuffix='_noSNR'
	
	# plot R(P)
	f, ax = plt.subplots()
	ax.set_title('Period Ratio Outer Planet'.format(suffix))
	helpers.set_axes(ax, epos, Trim=True)

	ax.set_ylabel('P2/P1')
	ax.set_ylim(0.1,100)

	ax.set_yscale('log')

	ax.axhspan(1.2, 4.0, facecolor='0.5', alpha=0.5)
	ax.axhline(2.2, color='0.5', ls='-')
		
	for k, sg in enumerate(epos.groups):
		subset= sim['i sg']==k
		ax.plot(sim['P'][subset], sim['dP'][subset], ls='', marker='.', mew=0, ms=5.0, color=clrs[k % 4], label=sg['name'])

	
	#ax.legend(loc='lower left', shadow=False, prop={'size':14}, numpoints=1)
	helpers.save(plt, '{}tests/out_Pratio{}'.format(epos.plotdir,fsuffix))

def hist_Pratio(epos, SNR=True, Parametric=False):

	sim=epos.synthetic_survey
	
	for k, sg in enumerate(epos.groups):
		f, ax = plt.subplots()
		ax.set_title('Period Ratio Outer Planet {}'.format(sg['name']))

		ax.set_xlabel('P2/P1')
		ax.set_xlim(1,10)

		ax.axvspan(1.2, 4.0, facecolor='0.5', alpha=0.5)
		ax.axvline(2.2, color='0.5', ls='-',label='Kepler')
		
		bins=np.linspace(0,10,21)
		
		# SNR
		subset= sim['i sg']==k
		aN= np.isfinite(sim['dP'])
		ax.hist(sim['dP'][subset&aN], bins=bins, color=clrs[k % 4], normed=True, label='Simulated')
		
		# all
		aN= np.isfinite(sg['all_Pratio'])
		ax.hist(sg['all_Pratio'][aN], bins=bins, color='k', fill=False, normed=True, label='Input')
		
		ax.legend(loc='upper right', shadow=False, prop={'size':14}, numpoints=1)
		helpers.save(plt, '{}tests/hist_Pratio.{}'.format(epos.plotdir,sg['name']))
