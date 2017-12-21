import numpy as np

def periodradius(epos, Init=False, fpara=None, xbin=None, ybin=None, xgrid=None, ygrid=None):
	''' return the period-radius distribution'''
	# normalisation does not make sense, use 
	# - per unit dlnPdlnR (*epos.scale)
	# - per grid cell
	if fpara is None:
		pps= epos.fitpars.get('pps',Init=Init)
		fpar2d= epos.fitpars.get2d(Init=Init)
	else:
		pps= epos.fitpars.getmc('pps',fpara)
		fpar2d= epos.fitpars.get2d_fromlist(fpara)
		#print fpara
	
	_pdf= epos.func(epos.X_in, epos.Y_in, *fpar2d)
	_pdf_X, _pdf_Y= np.sum(_pdf, axis=1), np.sum(_pdf, axis=0)
	
	# calculate pdf on different grid?
	if xbin is not None:
		xgrid= np.logspace(np.log10(xbin[0]),np.log10(xbin[-1]),5)
	if ybin is not None:
		ygrid= np.logspace(np.log10(ybin[0]),np.log10(ybin[-1]),5)
	
	if (xgrid is not None) or (ygrid is not None):
		if xgrid is None:
			xgrid= epos.MC_xvar
		if ygrid is None:
			ygrid= epos.MC_yvar
	
		X,Y=np.meshgrid(xgrid, ygrid,indexing='ij')
		pdf= epos.func(X,Y, *fpar2d)
		#pdf_X, pdf_Y= np.sum(pdf, axis=1), np.sum(pdf, axis=0)
		
		# normalized per unit dlnxdlny
		pdf= pps* pdf/np.sum(_pdf)* epos.scale

		dlnx= np.log(xgrid[-1]/xgrid[0])
		dlny= np.log(ygrid[-1]/ygrid[0])

		pdf_X= np.average(pdf, axis=1) * dlny
		pdf_Y= np.average(pdf, axis=0) * dlnx

	else:
		# normalized in units dlnx, dlny, and dlnxdlny
		pdf_X= pps* _pdf_X/np.sum(_pdf_X) * epos.scale_x
		pdf_Y= pps* _pdf_Y/np.sum(_pdf_Y) * epos.scale_in_y
		pdf= pps* _pdf/np.sum(_pdf)* epos.scale
	
	return pps, pdf, pdf_X, pdf_Y
