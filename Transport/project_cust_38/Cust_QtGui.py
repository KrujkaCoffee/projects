from PyQt5 import QtGui


def sozdat_obj_pod_risovane(putf, lbl):
    lbl.setScaledContents(True)
    fon = QtGui.QPixmap(putf)
    wind_k_width =  lbl.width() / fon.width()
    wind_k_height = lbl.height() / fon.height()
    pixmap = fon.scaled(lbl.width(), lbl.height()).copy()
    return [pixmap,wind_k_width,wind_k_height]

def zagruzit_img_na_lbl(imgg,pixmap):
    imgg.setPixmap(pixmap)
    return

def ris_krug(qp,x,y,r):
    qp.setPen(QtGui.QColor(5, 5, 5))
    qp.setBrush(QtGui.QColor(200, 30, 40))
    qp.drawEllipse(int(x-r/2), int(y-r/2), r, r)


def ris_kvadrat(qp,x,y,v,s,r,g,b):
    qp.setPen(QtGui.QColor(5, 5, 5))
    qp.setBrush(QtGui.QColor(r, g, b))
    #qp.drawEllipse(int(x-r/2), int(y-r/2), r, r)
    qp.drawRect(int(x),int(y),int(v),int(s))

def ris_line(qp,x,y,x2,y2):
    if x2 == 0 or y2 == 0:
        return
    pen = QtGui.QPen(QtGui.QColor(200, 30, 40), 5, QtCore.Qt.DotLine)
    pen.setStyle(QtCore.Qt.DashLine)
    qp.setPen(pen)
    qp.setBrush(QtGui.QColor(200, 30, 40))
    qp.drawLine(int(x),int(y),int(x2),int(y2))

def ris_text(qp,x,y,text,r=255,g=255,b=55, razm_shrifta = 12, ima_font = 'Decorative'):
    ##qpp.drawText(nach[0] , nach[1] + i * shag1, 400,999, 0x1000, f'{spis_po_prof[i][0]} \n {spis_po_prof[i][-1]} баллов.')
    qp.setFont(QtGui.QFont(ima_font, int(razm_shrifta),5,True))
    qp.setPen(QtGui.QColor(r, g, b))
    qp.drawText(int(x),int(y),str(text))
    
