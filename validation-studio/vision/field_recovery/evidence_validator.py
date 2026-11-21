import re
from .description_reconstructor import ambiguous,complete

def qualify(candidate):
 field=candidate['field'];value=candidate['normalized_value'];reasons=[]
 if not candidate.get('spatial_verified',True):reasons.append('insufficient_spatial_evidence')
 if field=='descricao':
  if not complete(value):reasons.append('incomplete_description')
  if ambiguous(value,field):reasons.append('ambiguous_glyphs_not_normalized')
 if field in ['qtde','lastro'] and not re.fullmatch(r'\d{1,9}',value):reasons.append('not_quantity_token')
 if field=='sku' and (candidate.get('matches_large_printed_number') or candidate.get('matches_SSCC_body')):reasons.append('cross_assignment_from_printed_identifier')
 candidate['qualification_reasons']=reasons;candidate['status']='insufficient_evidence' if reasons else 'candidate';return not reasons

