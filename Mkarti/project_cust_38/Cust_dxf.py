import sys
import ezdxf
import project_cust_38.Cust_Functions as F
#pip install git+git://github.com/BebeSparkelSparkel/MinimumBoundingBox.git@master
from project_cust_38.MinimumBoundingBox import MinimumBoundingBox


def load_dxf(file):
    doc = False
    try:
        doc = ezdxf.readfile(file)
    except IOError:
        print(f"Not a DXF file or a generic I/O error.")
        return doc
    except ezdxf.DXFStructureError:
        print(f"Invalid or corrupted DXF file.")
        return doc
    return doc

def uchet_elems(item, set_points, perimetr, elems):
    # type_elem = item.dxftype()
    # print(type_elem)
    if item.dxftype() == "LINE":
        elems += 1
        dx = item.dxf.end.x - item.dxf.start.x
        dy = item.dxf.end.y - item.dxf.start.y
        leight = (dx ** 2 + dy ** 2) ** 0.5
        perimetr += leight
        set_points.add((item.dxf.start.x, item.dxf.start.y))
        set_points.add((item.dxf.end.x, item.dxf.end.y))
    if item.dxftype() == 'ELLIPSE':
        elems += 1
        xold = ""
        yold = ''
        for fl in item.flattening(distance=10):
            if xold != '':
                dx = fl[0] - xold
                dy = fl[1] - yold
                leight = (dx ** 2 + dy ** 2) ** 0.5
                perimetr += leight
            xold = fl[0]
            yold = fl[1]
            set_points.add((fl[0], fl[1]))
    if item.dxftype() == 'ARC':
        elems += 1
        xold = ""
        yold = ''
        for fl in item.flattening(round(item.dxf.radius / 50, 1) + 0.1):
            if xold != '':
                dx = fl[0] - xold
                dy = fl[1] - yold
                leight = (dx ** 2 + dy ** 2) ** 0.5
                perimetr += leight
            xold = fl[0]
            yold = fl[1]
            set_points.add((fl[0], fl[1]))
    if item.dxftype() == 'CIRCLE':
        elems += 1
        perimetr += item.dxf.radius * 3.14 * 2
        for fl in item.flattening(round(item.dxf.radius / 50, 1) + 0.1):
            set_points.add((fl[0], fl[1]))
    return set_points, perimetr, elems


def raschet_dxf(file):
    doc = load_dxf(file)
    # iterate over all entities in modelspace
    if doc == False:
        return 
    msp = doc.modelspace()

    set_points = set()
    perimetr = 0
    elems = 0
    for e in msp:
        if e.dxftype() == 'INSERT':
            for item in e.virtual_entities():
                set_points, perimetr, elems = uchet_elems(item,set_points, perimetr, elems)
        else:
            set_points, perimetr, elems = uchet_elems(e, set_points, perimetr, elems)
    #points = ( (1,2), (5,4), (-1,-3) )
    spis_points = list(set_points)
    if spis_points == []:
        for block in doc.blocks:
            for e in block:
                if e.dxftype() == 'INSERT':
                    for item in e.virtual_entities():
                        set_points, perimetr, elems = uchet_elems(item, set_points, perimetr, elems)
    spis_points = list(set_points)
    if spis_points == []:
        return {'rect_lmm':0,'rect_hmm':0,
            'rect_area_mm2':0,'elems':0,'perimetr_elems_mm':0}
    bounding_box = MinimumBoundingBox(spis_points) # returns namedtuple
    minor = min(bounding_box.length_parallel, bounding_box.length_orthogonal)
    major = max(bounding_box.length_parallel, bounding_box.length_orthogonal)
    bounding_box.area  # 16
    #print(bounding_box.unit_vector_angle*57.29577951308)
    return {'rect_lmm':round(major,2),'rect_hmm':round(minor,2),
            'rect_area_mm2':round(bounding_box.area,2),'elems':elems,'perimetr_elems_mm':round(perimetr,2)}


#file = 'P:\Python\Tehkart' + F.sep() + 'krug.dxf'
#'S3 Ст3сп5 КЛ.1905178.01.223 Полоса 2шт.dxf'КЛ.1905178.01.041 Лопасть_Лекало2
#print(raschet_dxf(file))
