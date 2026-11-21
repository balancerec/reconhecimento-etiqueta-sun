from .evidence_validator import qualify

def rank(candidates):
 qualified=[c for c in candidates if qualify(c)];values=sorted({c['normalized_value'] for c in qualified})
 return {'value':values[0] if len(values)==1 else None,'status':'conflicting' if len(values)>1 else ('accepted_candidate' if values else ('insufficient_evidence' if candidates else 'missing')),'candidates':candidates,'qualified_values':values,'confidence_calibrated':None,'human_review_required':True,'selection_policy':'unique qualified observed value only; no majority or ground-truth selection'}

