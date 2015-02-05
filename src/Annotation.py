# author: Muhammet Bastan, mubastan@gmail.com
# date: August 2011

import os
import glob
import numpy
import scipy
from PyQt4.QtGui import *

# whole image annotation labels
LPOS, LNEG, LSKIP = 1, -1, 0

# difficulty level: 
# skip: no label (default)
# simple L1: one object on clean background
# simple L2: multiple objects on clean background
# medium L3: single/multiple objects, but not cluttered
# difficult L4: cluttered
# very difficult L5: very hard or impossible to identify the contents
L0, L1, L2, L3, L4, L5 = 0, 1, 2, 3, 4, 5

# view type:
# skip V0: no label
# good view V1: a typical, easy to recognize view @ zero angle
# moderate V2: at some angle, but clearly visible
# side view V3: side, hard to recognize view
V0, V1, V2, V3 = 0, 1, 2, 3

# set
# S0: skip this image, do not use it
# STR: in the training set
# STS: in the test set
S0, STR, STS = 0, 1, -1

# One object selected by the user
class XObject:
    def __init__(self, mask=None, region=None, x1=0, y1=0, id = 0, w = 0, h = 0, view = V0, label = LPOS ):
        self.mask = mask
        self.region = region
        self.view = view      # default view label, no label
        self.label = label   # default object label: positive
        self.x1, self.y1, self.w, self.h = x1, y1, w, h
        if region:
            self.w, self.h = region.width(), region.height()
        self.id = id
        self.saveMask = True
        
    def deleteMask(self):
        if not self.mask: return
        m = self.mask
        self.mask = None
        del m
    def loadObjectMask(self, fname, forceLoad=False):
        if self.mask and not forceLoad: return
        if os.path.exists(fname):
            self.mask = QImage(fname)
            self.saveMask = True
        else:
            self.mask = None
            print 'Error! Object mask file does not exist: ', fname         
    def loadObjectImage(self, fname, brushColor, forceLoad=False):
        if self.region and not forceLoad: return
        if not self.mask: self.loadObjectMask(fname)
        if self.mask: self.region = self.getObjectRegion(brushColor)
        else:
            self.region = None
            print 'Could not load object image from mask file ', fname        
    # the image region to be shown on the object list scene
    def getObjectRegion(self, brushColor):
        cmask = self.mask.copy(self.x1, self.y1, self.w, self.h)
        rqimg = QImage(self.w, self.h, QImage.Format_ARGB32_Premultiplied)
        rqimg.fill(brushColor.rgba())
        painter = QPainter(rqimg) 
        painter.setCompositionMode(QPainter.CompositionMode_ColorBurn)     
        painter.drawImage(0,0,cmask)
        painter.end()
        return rqimg    
    def save(self, fname):
        if self.mask and self.saveMask:
            if not self.mask.save(fname):
                print 'Error saving object mask ', self.id, ' to ', fname                
            print 'Object mask saved to ', fname
            self.saveMask = False

# One image, containing the selected objects
class XImage:
    def __init__(self, fname=None, label = LSKIP, set = S0, level = L0):
        self.label = label      # image label: positive/negative/skip
        self.set = set           # training/test/skip set, default S0 (skip--tbd)
        self.level = level         # difficulty level, default L0 (skip--tbd)
        self.fname = fname
        self.objects = []
    
    def numObjects(self):
        return len(self.objects)
    def mask(self, index):
        if index < len(self.objects): return self.objects[index].mask
    def addObject (self, mask, region, x1, y1, id):
        obj = XObject(mask, region, x1, y1, id)
        self.objects.append(obj)
    def deleteObject(self, id):
        for obj in self.objects:
            if id == obj.id:
                self.objects.remove(obj)
    def deleteObjectMasks(self):
        for obj in self.objects:
            obj.deleteMask()
    def deleteAllObjects(self):
        del self.objects[:]    
    def saveObjectMasks(self, annotationDir):
        for i in range(self.numObjects()):
            imgName = os.path.splitext(self.fname)[0]            
            fname = annotationDir + imgName + '.' + str(i) + '.png'
            self.objects[i].save(fname)
        # delete unused masks from the disk
        i = self.numObjects()
        while True:
            imgName = os.path.splitext(self.fname)[0]            
            fname = annotationDir + imgName + '.' + str(i) + '.png'
            if not os.path.exists(fname): return
            else: os.remove(fname)
            
    def loadObjectMasks(self, annotationDir, forceLoad=False):
        imgName = os.path.splitext(self.fname)[0]            
        for i in range(self.numObjects()):
            fname = annotationDir + imgName + '.' + str(i) + '.png'
            if os.path.exists(fname):
                self.objects[i].loadObjectMask(fname, forceLoad)
    def loadObjectImages(self, annotationDir, brushColor, forceLoad=False):
        imgName = os.path.splitext(self.fname)[0]
        delList = []
        for i in range(self.numObjects()):
            fname = annotationDir + imgName + '.' + str(i) + '.png'
            if os.path.exists(fname):
                self.objects[i].loadObjectImage(fname, brushColor, forceLoad)
            else: delList.append(self.objects[i].id)                
        for id in delList:
                self.deleteObject(id)
                
    def toString(self):
        lineStr = str(self.set) + ' ' + str(self.level) + ' ' + str(self.label) + ' ' + str(self.numObjects()) + ' ' + self.fname
        for obj in self.objects:
            lineStr += ' ' + str(obj.view) + ' ' + str(obj.label) + ' ' + str(obj.x1) + ' ' + str(obj.y1) + ' ' + str(obj.w) + ' ' + str(obj.h)
        return lineStr
        
# all annotations, list of images + objects + object MBRs        
class Annotation:
    def __init__(self, fname=None):
        
        self.images = []
        self.index = 0      # index of the current image
        self.className =  "none"
        self.subclassName =  "none"
        self.folder = "none"
        self.dirPath = "./"
        self.annotationDir = self.dirPath + "annotation/"
        self.annfilename = fname
        if fname:
            self.loadAnnotation(fname)
    
    def prev(self):
        ind = self.index - 1
        if ind < 0: ind = 0
        return ind
    def next(self):
        ind = self.index + 1
        if ind >= self.numImages(): ind = self.numImages() - 1
        return ind
    def goto(self, index):
        if index >= 0 and index < self.numImages(): self.index = index
        return self.index
    def numImages(self):
        return len(self.images)
        
    def image(self, index):
        if index < self.numImages(): return self.images[index]
        else: return None
    def curImage(self):
        return self.image(self.index)
    def imageName(self, index):
        if index < self.numImages(): return self.images[index].fname
        else: return ""
    def curImagePath(self):
        return self.imagePath(self.index)
    def imagePath(self, index):
        if index < self.numImages(): return self.dirPath + self.images[index].fname
        else: return ""
    def numObjects(self, index):
        if index < self.numImages(): return self.images[index].numObjects()
        else: return 0
    
    def setClassName(self, className, subclassName):
        self.className = str(className)
        self.subclassName = str(subclassName)        
        annDir = str(self.rootPath + 'annotation/')
        if self.subclassName != "none": annDir += self.subclassName
        elif self.className != "none": annDir += self.className
        self.setAnnotationDir(annDir)
        
    def setAnnotationDir(self, dir):
        if not os.path.isdir(dir):            
            os.makedirs(dir)
            print dir, ' did not exist! Created..'
        self.annotationDir = dir + "/"
        print 'Annotation directory changed to : ', self.annotationDir
    
    def setLabel(self, label):
        if label in (-1, 0, 1):
            self.curImage().label = label
        elif label in (-2, 10, 2):
            for i in range(self.numImages()):
                if label == -2: label = -1
                elif label == 10: label = 0
                elif label == 2: label = 1
                self.image(i).label = label
    
    # add object to image @index location   
    def addObjectTo(self, index, mask, region, x1, y1, id):
        if index < self.numImages():
            self.images[index].addObject (mask, region, x1, y1, id)
    # add object to current image
    def addObject (self, mask, region, x1, y1, id):
        self.addObjectTo(self.index, mask, region, x1, y1, id)
    
    def deleteAllObjects(self):
        self.deleteAllObjectsAt(self.index)
    def deleteAllObjectsAt(self, index):
        if index < self.numImages(): self.images[index].deleteAllObjects()
    
    def deleteObjectMasks(self):
        self.deleteObjectMasksAt(self.index)
    def deleteObjectMasksAt(self, index):
        if index < self.numImages(): self.images[index].deleteObjectMasks()
        
    def deleteObjects(self, ids):
        self.deleteObjectsAt(self.index, ids)
    def deleteObjectsAt(self, index, ids):
        if index > self.numImages() or len(ids) == 0: return
        self.images[index].loadObjectMasks(self.annotationDir)
        for id in ids:
            self.images[index].deleteObject(id)
        
    def loadDir(self, dirPath, folderName, fileExt):
        print 'Directory: ', dirPath
        print 'Folder: ', folderName
        print 'File extension: ', fileExt
        self.rootPath = dirPath + '/'
        self.annotationDir = dirPath + '/annotation/'
        self.dirPath = str(dirPath) + '/color/'
        self.folder = str(folderName)
        self.fex = str(fileExt)
        chain = str(dirPath) + '/color/' + str(fileExt)
        #print chain
        # get all the files with the given extension (full path)
        imageFiles = glob.glob(chain)
        imageList = []
        # extract only the file names
        for f in imageFiles:
            imageList.append(os.path.basename(f))        
        # soft the file names
        imageList.sort(cmp=lambda x, y: cmp(x.lower(), y.lower()))        
        # add to the list of images
        for f in imageList:
            self.images.append(XImage(f))        
        print 'Number of images loaded: ', len(self.images)
        #print 'loadDir:', self.annotationDir
        
    # save the selected object masks of the current image as png images
    # in the directory /path/to/data/annotation/
    def saveCurrentObjectMasks(self):
        self.saveObjectMasks(self.index)   
                
    def saveObjectMasks(self, index):
        if self.numImages() == 0 or index >= self.numImages() : return
        if self.image(index).numObjects() == 0: return
        if not os.path.isdir(self.annotationDir):
            print self.annotationDir, ' does not exist! create it..'
            os.makedirs(self.annotationDir)        
        self.image(index).saveObjectMasks(self.annotationDir)
        print 'Saved object masks (selections)'
        
    # load the already saved object masks from the disk
    def loadObjectMasks(self, index, forceLoad=False):
        if self.numImages() == 0 or index >= self.numImages() : return
        self.images[index].loadObjectMasks(self.annotationDir, forceLoad)
    def loadObjectImages(self, index, brushColor, forceLoad=False):
        if self.numImages() == 0 or index >= self.numImages() : return
        self.images[index].loadObjectImages(self.annotationDir, brushColor, forceLoad)
    
    def getAnnotationListFile(self):
        filename = self.folder
        if len(self.className) > 0 and self.className != 'none': filename += '.' + self.className
        if len(self.subclassName) > 0 and self.subclassName != 'none': filename += '.' + self.subclassName
        filename += '.txt'
        return filename
        
    def saveAnnotationList(self):        
        #if self.annfilename is None:
        self.annfilename = self.annotationDir + self.getAnnotationListFile()
        self.saveAnnotationListAs(self.annfilename)        
    
    def saveAnnotationListAs(self, fname):
        if self.numImages() == 0: print 'Nothing to save yet!'; return    
        ofs = open(fname, 'w')
        if not ofs: print 'Could not open file to save!'; return    
        ofs.write( self.className + ' ' + self.subclassName )
        ofs.write('\n')
        ofs.write( self.dirPath + ' ' + self.folder )
        ofs.write('\n')
        ofs.write( self.annotationDir + ' ' + self.subclassName )
        ofs.write('\n')
        ofs.write(str(self.numImages()))        
        for image in self.images:
            ofs.write('\n')
            ofs.write(image.toString())        
        ofs.close()
        self.annfilename = fname
        print 'Annotation list saved to: ', fname
    
    def loadAnnotation(self, fname):
        ifs = open(fname)
        if not ifs:
            print 'Could not load ', fname
            return
        line = ifs.readline()
        self.className, self.subclassName = line.split()
        line = ifs.readline()
        self.dirPath, self.folder = line.split()
        self.rootDir = self.dirPath      # this is not correct
        line = ifs.readline()
        self.annotationDir = line.split()[0]
        ifs.readline()
        # read images and objects
        for line in ifs:
            self.images.append(self.parseLine(line))
        print 'Loaded ', fname
        print 'Number of images in the annotation list: ', self.numImages()
        ifs.close()
    
    # initial version
    def parseLine0(self, line):
        tokens = line.split()
        # XImage(self, fname=None, label = LSKIP, set = S0, level = L0)
        ximg = XImage(tokens[2], int(tokens[0]))        
        # objects
        for i in range(int(tokens[1])):
            # XObject(self, mask=None, region=None, x1=0, y1=0, id = 0, w = 0, h = 0, view = V0, label = LPOS )
            xobj = XObject(None, None, int(tokens[4*i+3]), int(tokens[4*i+4]), i, int(tokens[4*i+5]), int(tokens[4*i+6]) )
            ximg.objects.append(xobj)
        return ximg
    # updated version (22 October 2011)
    def parseLine(self, line):
        tokens = line.split()
        # XImage(self, fname=None, label = LSKIP, set = S0, level = L0)
        ximg = XImage(tokens[4], int(tokens[2]), int(tokens[0]), int(tokens[1]))        
        # objects
        for i in range(int(tokens[3])):
            # XObject(self, mask=None, region=None, x1=0, y1=0, id = 0, w = 0, h = 0, view = V0, label = LPOS )
            xobj = XObject(None, None, int(tokens[6*i+7]), int(tokens[6*i+8]), i, int(tokens[6*i+9]), int(tokens[6*i+10]), int(tokens[6*i+5]), int(tokens[6*i+6]) )
            ximg.objects.append(xobj)
        return ximg
        
        
def getMBR_numpy(qimage):
    x1, y1, x2, y2 = -1, -1, -1, -1
    if qimage:
        qimage.save("tmp.png")
        nimg = scipy.misc.imread('tmp.png')
        r,c = numpy.where(nimg > 0)
        if len(r) > 0:      # check if there is any FG pixel
            x1, y1, x2, y2 = c.min(), r.min(), c.max(), r.max() 
    return x1, y1, x2-x1+1, y2-y1+1