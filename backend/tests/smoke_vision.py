from PIL import Image, ImageDraw, ImageFont
import numpy as np
from vision import recognize_labels, health

font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',32)
def label(color,lines):
    image=Image.new('RGB',(900,850),color);d=ImageDraw.Draw(image)
    for i,text in enumerate(lines):d.text((35,35+i*75),text,font=font,fill='black')
    return image

def run():
    assert health()['engines']['rapidocr']
    dun=label('white',['375825','PR PATO GERM LIMP SANIT MARINE','750ML 12','FABR:11/2026','VENC:11/2028','LOTE:8428857','D344924','17894650013578'])
    sun=label('#22badd',['ITEM: 387279 GLADE LAVANDA','QTDE: 294','LASTRO: 49','VALIDADE: 2 ANO','LT: 001234','DOC ENTRADA: 5083530012'])
    for image,kind,sku in [(dun.rotate(90,expand=True),'DUN','375825'),(sun,'SUN','387279')]:
        labels,processing=recognize_labels(np.array(image))
        found=next((v for v in labels if v['label_type']==kind),None)
        assert found is not None,(kind,labels)
        assert found['fields']['sku']==sku,(kind,found['fields'],found['ocr_conflicts'])
        if kind=='DUN':assert found['fields']['units_per_case']==12,found['fields']
        else:assert found['fields']['quantity_boxes']==294,found['fields']
        print('Synthetic OCR OK:',kind,processing,flush=True)
    # Two independent labels on the same image must keep their SKUs separate.
    canvas=Image.new('RGB',(1940,980),'#272727');canvas.paste(dun,(30,40));canvas.paste(sun,(1000,40))
    labels,processing=recognize_labels(np.array(canvas))
    assert {'375825','387279'}.issubset({l['fields']['sku'] for l in labels}),[(v['label_type'],v['fields']) for v in labels]
    print('Synthetic multi-label OCR OK:',processing,flush=True)
if __name__=='__main__':run()
