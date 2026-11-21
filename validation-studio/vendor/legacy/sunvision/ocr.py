"""Explicit ORT sessions; GPU availability alone is never proof of inference."""
import collections, hashlib, importlib.metadata as md,json,os,time
from pathlib import Path
import onnxruntime as ort
class OCR:
    def __init__(self,mode,profile_dir,allow_cpu_partition=True):
        if mode not in ['cpu','cuda']: raise ValueError(mode)
        self.mode=mode; self.profile_dir=Path(profile_dir); self.profile_dir.mkdir(parents=True,exist_ok=True); self.sessions=[]; self.dll_handles=[]; self.calls=[]; self.allow_cpu_partition=allow_cpu_partition
        names=[d.metadata['Name'].lower() for d in md.distributions()]
        if 'onnxruntime' in names and 'onnxruntime-gpu' in names: raise RuntimeError('Conflicting ORT distributions; not modifying dependencies automatically')
        if mode=='cuda':
            root=Path(ort.__file__).parent.parent/'nvidia'; folders=sorted({p.parent for p in root.rglob('*.dll')}); os.environ['PATH']=os.pathsep.join(map(str,folders))+os.pathsep+os.environ.get('PATH','')
            for folder in folders:
                if hasattr(os,'add_dll_directory'): self.dll_handles.append(os.add_dll_directory(str(folder)))
            ort.preload_dlls(directory='')
        import rapidocr_onnxruntime.utils.infer_engine as ie
        from rapidocr_onnxruntime import RapidOCR
        original=ie.InferenceSession
        def session(model,sess_options=None,providers=None,**kwargs):
            opts=sess_options or ort.SessionOptions(); opts.intra_op_num_threads=4; opts.inter_op_num_threads=1; opts.enable_profiling=True; opts.log_severity_level=2; opts.profile_file_prefix=str(self.profile_dir/Path(model).stem)
            if not allow_cpu_partition: opts.add_session_config_entry('session.disable_cpu_ep_fallback','1')
            eps=[('CUDAExecutionProvider',{'device_id':0,'cudnn_conv_algo_search':'HEURISTIC'}),'CPUExecutionProvider'] if mode=='cuda' else ['CPUExecutionProvider']
            s=ort.InferenceSession(model,sess_options=opts,providers=eps,**kwargs); s.disable_fallback(); self.sessions.append({'model':str(model),'sha256':hashlib.sha256(Path(model).read_bytes()).hexdigest(),'session':s})
            if mode=='cuda' and s.get_providers()[0]!='CUDAExecutionProvider': raise RuntimeError('Whole-session CPU fallback rejected')
            return s
        # RapidOCR's session factory has no public injection hook. Patch only during construction,
        # restore immediately; instantiate sequentially, never from concurrent threads.
        ie.InferenceSession=session
        try: self.engine=RapidOCR(det_use_cuda=mode=='cuda',cls_use_cuda=mode=='cuda',rec_use_cuda=mode=='cuda')
        except Exception:
            self.close(); raise
        finally: ie.InferenceSession=original
    def __call__(self,image):
        start=time.perf_counter(); rows,_=self.engine(image); self.calls.append({'shape':list(image.shape),'seconds':time.perf_counter()-start})
        return [{'id':i,'text':r[1],'confidence':float(r[2]),'polygon_local':r[0],'confidence_semantics':'uncalibrated OCR score'} for i,r in enumerate(rows or [])]
    def close(self):
        entries=[]; total=collections.Counter()
        for entry in self.sessions:
            s=entry['session']; file=Path(s.end_profiling()); events=json.loads(file.read_text(encoding='utf-8')); counts=collections.Counter(); ops=collections.Counter()
            for e in events:
                a=e.get('args',{}); ep=a.get('provider')
                if ep: counts[ep]+=1; ops[(ep,a.get('op_name','?'),e['name'])]+=1
            total.update(counts); entries.append({'model':entry['model'],'model_sha256':entry['sha256'],'profile':str(file),'profile_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'configured_providers':s.get_providers(),'events_by_provider':dict(counts),'operators':[{'provider':ep,'op':op,'node':node,'events':n} for (ep,op,node),n in ops.items()]})
        self.sessions=[]
        return {'requested':self.mode,'effective':'CUDA+CPU' if total['CUDAExecutionProvider'] and total['CPUExecutionProvider'] else ('CUDA' if total['CUDAExecutionProvider'] else ('CPU' if total['CPUExecutionProvider'] else 'unproven')),'cuda_proven':bool(total['CUDAExecutionProvider']),'events_by_provider':dict(total),'profiles':entries,'calls':self.calls,'fallback_policy':'CPU partition allowed and reported; whole-session/runtime retry rejected','evidence_scope':'one source image per OCR instance, all regions/orientation trials and warmup included'}

