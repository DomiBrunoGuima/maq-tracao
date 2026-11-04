import pymupdf as fitz, sys
old=fitz.open('../Apresentacao e Manual - Sistema de Ensaios.pdf')
new=fitz.open('novas.pdf')
out=fitz.open()
out.insert_pdf(old, from_page=0, to_page=2)
out.insert_pdf(new, from_page=0, to_page=1)
out.insert_pdf(old, from_page=5, to_page=17)
out.insert_pdf(new, from_page=2, to_page=new.page_count-1)
out.insert_pdf(old, from_page=20, to_page=20)
# capa
c=out[0]
for r in (fitz.Rect(50,349,440,373), fitz.Rect(50,418,260,435)):
    c.add_redact_annot(r, fill=False)
c.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
F='/usr/share/fonts/opentype/inter/Inter-Regular.otf'
def rgb(h): return tuple(int(h[i:i+2],16)/255 for i in (1,3,5))
c.insert_font(fontname='inter', fontfile=F)
c.insert_text((54,365.5),'Apresentação e manual completo',fontname='inter',fontsize=16.5,color=rgb('#b8c3d6'))
c.insert_text((54,430.5),'Versão 1.1 · Novembro de 2026',fontname='inter',fontsize=10.5,color=rgb('#6f7d95'))
out.set_metadata({'title':'Sistema de Ensaios de Tração e Flexão — Apresentação e Manual completo','author':'Automatic'})
out.save(sys.argv[1], garbage=3, deflate=True)
print(out.page_count)
