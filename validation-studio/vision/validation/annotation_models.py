from pydantic import BaseModel,Field,ConfigDict
from typing import Literal
FIELDS=('sku','descricao','qtde','lastro','lote','documento_entrada','validade_impressa','sscc')
class FieldAnnotation(BaseModel):
 model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
 value:str|None=Field(default=None,max_length=4096)
 visibility:Literal['unreviewed','visible_legible','visible_illegible','not_physically_present','out_of_frame']='unreviewed'
 reviewed:bool=False
 value_source:Literal['unreviewed','original_pixels','algorithm_suggestion','catalog_only']='unreviewed'
 notes:str=Field(default='',max_length=4096)
class CopyAnnotation(BaseModel):
 model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
 copy_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
 is_label:bool=True
 copy_reviewed:bool=False
 polygon_original:list[tuple[float,float]]=Field(default_factory=list,max_length=64)
 polygon_reviewed:bool=False
 visibility:Literal['unreviewed','complete','partial','indeterminate']='unreviewed'
 fields:dict[str,FieldAnnotation]=Field(default_factory=lambda:{f:FieldAnnotation() for f in FIELDS})
 confirmed_sscc:str|None=None
 identity_basis:Literal['unreviewed','direct_read','cross_photo_physical_confirmation']='unreviewed'
 identity_evidence_photo_ids:list[str]=Field(default_factory=list,max_length=64)
 identity_note:str=Field(default='',max_length=4096)
class AnnotationRequest(BaseModel):
 model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
 photo_id:str
 image_sha256:str
 expected_revision:int=Field(default=0,ge=0)
 prediction_run_id:str='v26-spatial'
 reviewer:str=Field(default='',max_length=128)
 review_mode:Literal['assisted','blind']='assisted'
 used_suggestions:bool=False
 exhaustive_instance_review:bool=False
 no_labels_confirmed:bool=False
 copies:list[CopyAnnotation]=Field(default_factory=list,max_length=64)
 notes:str=Field(default='',max_length=8192)

