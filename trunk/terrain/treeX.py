# -*- coding: utf-8 -*-
'''
Created on 11.12.2010
Based on Kwasi Mensah's (kmensah@andrew.cmu.edu) "The Fractal Plants Sample Program" from 8/05/2005
@author: Praios

Edited by Craig Macomber

Created on Thu Nov 24 19:35:08 2011
based on the above authors and editors
@author: Shawn Updegraff
'''

import sys

from panda3d.core import NodePath, Geom, GeomNode, GeomVertexArrayFormat, TransformState, GeomVertexWriter, GeomTristrips, GeomVertexRewriter, GeomVertexReader, GeomVertexData, GeomVertexFormat, InternalName
from panda3d.core import Mat4, Vec3, CollisionNode, CollisionTube, Point3, Quat
from math import sin,cos,pi
import random
from collections import namedtuple

#from panda3d.core import PStatClient
#PStatClient.connect()

_DoLeaves_ = 0
_polySize = 16

def _randomBend(inQuat, maxAngle=20):
    q=Quat()
    theta = random.randint(-maxAngle,maxAngle)
    phi = random.randint(-maxAngle,maxAngle)
   
    #power of 2 here makes distrobution even withint a circle
    # (makes larger bends are more likley as they are further spread)
#    ammount=(random.random()**2)*maxAngle
    q.setHpr((0,theta,phi))
    return inQuat*q


# TODO : This needs to get updated to work with quat. Using tmp hack.
def _angleRandomAxis(quat, angle):
#     fwd = quat.getUp()
#     perp1 = quat.getRight()   
#     perp2 = quat.getForward() 
#     nangle = angle + math.pi * (0.125 * random.random() - 0.0625)
#     nfwd = fwd * (0.5 + 2 * random.random()) + perp1 * math.sin(nangle) + perp2 * math.cos(nangle)
#     nfwd.normalize()
#     nperp2 = nfwd.cross(perp1)
#     nperp2.normalize()
#     nperp1 = nfwd.cross(nperp2)
#     nperp1.normalize()
    return _randomBend(quat,angle)




class FractalTree(NodePath):
    __format = None
    def __init__(self, barkTexture, leafModel, lengthList, numCopiesList, radiusList):
        NodePath.__init__(self, "Tree Holder")
        self.numPrimitives = 0
        self.leafModel = leafModel
        self.barkTexture = barkTexture
        self.bodies = NodePath("Bodies")
        self.leaves = NodePath("Leaves")
        self.coll = self.attachNewNode(CollisionNode("Collision"))   
        self.bodydata = GeomVertexData("body vertices", self.__format, Geom.UHStatic)
        self.numCopiesList = list(numCopiesList)   
        self.radiusList = list(radiusList) 
        self.lengthList = list(lengthList) 
        self.iterations = 1
        
#        self.makeEnds()
#        self.makeFromStack(True)
        self.coll.show()       
        self.bodies.setTexture(barkTexture)
        self.coll.reparentTo(self)
        self.bodies.reparentTo(self)
        self.leaves.reparentTo(self)
       
    #this makes a flattened version of the tree for faster rendering...
    def getStatic(self):
        np = NodePath(self.node().copySubgraph())
        np.flattenStrong()
        return np       
   
    #this should make only one instance
    @classmethod
    def makeFMT(cls):
        if cls.__format is not None:
            return
        formatArray = GeomVertexArrayFormat()
        formatArray.addColumn(InternalName.make("drawFlag"), 1, Geom.NTUint8, Geom.COther)   
        format = GeomVertexFormat(GeomVertexFormat.getV3n3t2())
        format.addArray(formatArray)
        cls.__format = GeomVertexFormat.registerFormat(format)
   
    def makeEnds(self, pos=Vec3(0, 0, 0), quat=None):
        if quat is None: quat=Quat()
        self.ends = [(pos, quat, 0)]
       
    def makeFromStack(self, makeColl=False):
        stack = self.ends
        to = self.iterations
        lengthList = self.lengthList
        numCopiesList = self.numCopiesList
        radiusList = self.radiusList
        ends = []
        while stack:
            pos, quat, depth = stack.pop()
            print depth
            length = lengthList[depth]
            if depth != to and depth + 1 < len(lengthList):
                self.drawBody(pos, quat, radiusList[depth])     
                #move foward along the right axis
                newPos = pos + quat.getUp() * length
                if makeColl:
                    self.makeColl(pos, newPos, radiusList[depth])
                numCopies = numCopiesList[depth] 
                if numCopies:       
                    for i in xrange(numCopies):
#                        stack.append((newPos, _angleRandomAxis(quat, 2 * math.pi * i / numCopies), depth + 1))
                        stack.append((newPos, _randomBend(quat, self.maxAngle), depth + 1))
                        # 
                        #stack.append((newPos, _randomAxis(vecList,3), depth + 1))
                else:
                    #just make another branch connected to this one with a small variation in direction
                    stack.append((newPos, _randomBend(quat, self.maxBend), depth + 1))
            else:
                self.drawBody(pos, quat, radiusList[depth], False)
                if _DoLeaves_: self.drawLeaf(pos, quat)
                ends.append((pos, quat, depth))
        self.ends = ends
        
       
    def makeColl(self, pos, newPos, radius):
        tube = CollisionTube(Point3(pos), Point3(newPos), radius)
        self.coll.node().addSolid(tube)
         
    #this draws the body of the tree. This draws a ring of vertices and connects the rings with
    #triangles to form the body.
    #this keepDrawing paramter tells the function wheter or not we're at an end
    #if the vertices before you were an end, dont draw branches to it
    def drawBody(self, pos, quat, radius=1,UVcoord=(1,1), keepDrawing=True, numVertices=_polySize):
        vdata = self.bodydata
        circleGeom = Geom(vdata)
        vertWriter = GeomVertexWriter(vdata, "vertex")
        #colorWriter = GeomVertexWriter(vdata, "color")
        normalWriter = GeomVertexWriter(vdata, "normal")
#        drawReWriter = GeomVertexRewriter(vdata, "drawFlag")
        texReWriter = GeomVertexRewriter(vdata, "texcoord")

        startRow = vdata.getNumRows()
        vertWriter.setRow(startRow)
        #colorWriter.setRow(startRow)
        normalWriter.setRow(startRow)       

#        sCoord = 0   
#        if (startRow != 0):
#            texReWriter.setRow(startRow - numVertices) #go back numVert in the vert list
#            sCoord = texReWriter.getData2f().getX() + _Vscale           # UV SCALE HERE!
#            print sCoord
#            drawReWriter.setRow(startRow - numVertices)
#            if(drawReWriter.getData1f() == False):
#                sCoord -= _Vscale                                # UV SCALE HERE!
#        drawReWriter.setRow(startRow)
        texReWriter.setRow(startRow)   
       
        angleSlice = 2 * pi / numVertices
        currAngle = 0
        #axisAdj=Mat4.rotateMat(45, axis)*Mat4.scaleMat(radius)*Mat4.translateMat(pos)
        perp1 = quat.getRight()
        perp2 = quat.getForward()   
        #vertex information is written here
        for i in xrange(numVertices): 
            adjCircle = pos + (perp1 * cos(currAngle) + perp2 * sin(currAngle)) * radius
            normal = perp1 * cos(currAngle) + perp2 * sin(currAngle)       
            normalWriter.addData3f(normal)
            vertWriter.addData3f(adjCircle)
            texReWriter.addData2f(float(UVcoord[0]*i) / numVertices,UVcoord[1])            # UV SCALE HERE!
            print UVcoord
            #colorWriter.addData4f(0.5, 0.5, 0.5, 1)
#            drawReWriter.addData1f(keepDrawing)
            currAngle += angleSlice 
        drawReader = GeomVertexReader(vdata, "drawFlag")
        drawReader.setRow(startRow - numVertices)   
        
        #we cant draw quads directly so we use Tristrips
        if (startRow != 0) and (keepDrawing == False):
            lines = GeomTristrips(Geom.UHStatic)         
            for i in xrange(numVertices):
                lines.addVertex(i + startRow)
                lines.addVertex(i + startRow - numVertices)
            lines.addVertex(startRow)
            lines.addVertex(startRow - numVertices)
            lines.closePrimitive()
            #lines.decompose()
            circleGeom.addPrimitive(lines)           
            circleGeomNode = GeomNode("Debug")
            circleGeomNode.addGeom(circleGeom)   
            self.numPrimitives += numVertices * 2
            self.bodies.attachNewNode(circleGeomNode)
   
    #this draws leafs when we reach an end       
    def drawLeaf(self, pos=Vec3(0, 0, 0), quat=None, scale=0.125):
        #use the vectors that describe the direction the branch grows to make the right
        #rotation matrix
        newCs = Mat4()#0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
#         newCs.setRow(0, vecList[2]) #right
#         newCs.setRow(1, vecList[1]) #up
#         newCs.setRow(2, vecList[0]) #forward
#         newCs.setRow(3, Vec3(0, 0, 0))
#         newCs.setCol(3, Vec4(0, 0, 0, 1))   
        quat.extractToMatrix(newCs)
        axisAdj = Mat4.scaleMat(scale) * newCs * Mat4.translateMat(pos)       
        leafModel = NodePath("leaf")
        self.leafModel.instanceTo(leafModel)
        leafModel.reparentTo(self.leaves)
        leafModel.setTransform(TransformState.makeMat(axisAdj))

       
    def grow(self, num=1, removeLeaves=0, leavesScale=0, trunkRate = 0):
        self.iterations += num
        while num > 0:
            self.setScale(self, 1+trunkRate/100)
            self.leafModel.setScale(self.leafModel, (1+leavesScale/100) / (1+trunkRate/100) )
            if removeLeaves:
                for i,c in enumerate(self.leaves.getChildren()):
#                    print self.numCopiesList[i]
                    c.removeNode()
            self.makeFromStack()
            self.bodies.setTexture(self.barkTexture)         
            num -= 1


class flexibleTree(FractalTree):
    def __init__(self):       
        self.bodydata = GeomVertexData("body vertices", GeomVertexFormat.getV3n3t2(), Geom.UHStatic)

#        if maxAngle: self.maxAngle = maxAngle
#        if maxBend: self.maxBend = maxBend
        barkTexture = base.loader.loadTexture(_BarkTex_)
        leafModel = base.loader.loadModel('../resources/models/shrubbery')
        leafModel.clearModelNodes()
        leafModel.flattenStrong()
        leafTexture = base.loader.loadTexture(_LeafTex_)
        leafModel.setTexture(leafTexture, 1) 
        leafModel.setScale(0.1)
        leafModel.setTransparency(1)

        FractalTree.makeFMT()                
        FractalTree.__init__(self, barkTexture, leafModel, [1], [1], [1])
       
    def branchFromNodes(self,nodeList):
#        endNode = nodeList.pop() # need to set keepDraw False on last node
        for i,node in enumerate(nodeList):
            if i == 0: isRoot = True
            else: isRoot = False
            if i == len(nodeList): keepDrawing = True
            else: keepDrawing = False
            self.drawBody(node.pos, node.quat, node.radius,node.texUV,keepDrawing,isRoot)
#        self.drawBody(endNode.pos,endNode.quat,endNode.radius,endNode.texUV,keepDrawing=1) # tell drawBody this is the end of the branch

    #this draws the body of the tree. This draws a ring of vertices and connects the rings with
    #triangles to form the body.
    #this keepDrawing paramter tells the function wheter or not we're at an end
    #if the vertices before you were an end, dont draw branches to it
    def drawBody(self, pos, quat, radius=1,UVcoord=(1,1), keepDrawing=True, isRoot=False, numVertices=_polySize):
        print "subclass"
        if isRoot:
            self.bodydata = GeomVertexData("body vertices", GeomVertexFormat.getV3n3t2(), Geom.UHStatic)
        vdata = self.bodydata
        circleGeom = Geom(vdata) # this was originally a copy of all previous geom in vdata...
        vertWriter = GeomVertexWriter(vdata, "vertex")
        #colorWriter = GeomVertexWriter(vdata, "color")
        normalWriter = GeomVertexWriter(vdata, "normal")
#        drawReWriter = GeomVertexRewriter(vdata, "drawFlag")
        texReWriter = GeomVertexRewriter(vdata, "texcoord")

        startRow = vdata.getNumRows()
        vertWriter.setRow(startRow)
        #colorWriter.setRow(startRow)
        normalWriter.setRow(startRow)       
        texReWriter.setRow(startRow)   
       
        angleSlice = 2 * pi / numVertices
        currAngle = 0
        #axisAdj=Mat4.rotateMat(45, axis)*Mat4.scaleMat(radius)*Mat4.translateMat(pos)
        perp1 = quat.getRight()
        perp2 = quat.getForward()   
        #vertex information is written here
        for i in xrange(numVertices+1): 
            adjCircle = pos + (perp1 * cos(currAngle) + perp2 * sin(currAngle)) * radius
            normal = perp1 * cos(currAngle) + perp2 * sin(currAngle)       
            normalWriter.addData3f(normal)
            vertWriter.addData3f(adjCircle)
            texReWriter.addData2f(float(UVcoord[0]*i) / numVertices,UVcoord[1])            # UV SCALE HERE!
            #colorWriter.addData4f(0.5, 0.5, 0.5, 1)
#            drawReWriter.addData1f(keepDrawing)
            currAngle += angleSlice 
        
        #we cant draw quads directly so we use Tristrips
        if (startRow != 0) and (keepDrawing == False):
            lines = GeomTristrips(Geom.UHStatic)         
            for i in xrange(numVertices+1):
                lines.addVertex(i + startRow)
                lines.addVertex(i + startRow - numVertices-1)
            lines.addVertex(startRow)
            lines.addVertex(startRow - numVertices)
            lines.closePrimitive()
            #lines.decompose()
            circleGeom.addPrimitive(lines)           
            circleGeomNode = GeomNode("Debug")
            circleGeomNode.addGeom(circleGeom)   
            self.numPrimitives += numVertices * 2
            self.bodies.attachNewNode(circleGeomNode)
            
   
    #this draws leafs when we reach an end       
    def drawLeaf(self, pos=Vec3(0, 0, 0), quat=None, scale=0.125):
        #use the vectors that describe the direction the branch grows to make the right
        #rotation matrix
        newCs = Mat4()#0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
#         newCs.setRow(0, vecList[2]) #right
#         newCs.setRow(1, vecList[1]) #up
#         newCs.setRow(2, vecList[0]) #forward
#         newCs.setRow(3, Vec3(0, 0, 0))
#         newCs.setCol(3, Vec4(0, 0, 0, 1))   
        quat.extractToMatrix(newCs)
        axisAdj = Mat4.scaleMat(scale) * newCs * Mat4.translateMat(pos)       
        leafModel = NodePath("leaf")
        self.leafModel.instanceTo(leafModel)
        leafModel.reparentTo(self.leaves)
        leafModel.setTransform(TransformState.makeMat(axisAdj))
        
    def addBranch(self, rootNode, branchNodes):
        pass

FractalTree.makeFMT()
BranchNode = namedtuple('BranchNode','pos quat radius texUV')

if __name__ == "__main__":
#    random.seed(11*math.pi)
    L0 = 5
    R0 = 1
    lfact = 0.75
    rfact = .7
    numGens = 6
    _uvScale = (2,1) #repeats per unit length (around perimeter, along the tree axis) 
    _BarkTex_ = "../resources/models/barkTexture-1.jpg"
    _LeafTex_ = '../resources/models/material-12.png'
   
    from direct.showbase.ShowBase import ShowBase
    base = ShowBase()
    base.cam.setPos(0, -30, 10)
    base.setFrameRateMeter(1)
    tree = flexibleTree()
    tree.setTwoSided(1)    
    tree.reparentTo(base.render)
    
    root = []

    thisBranch = [BranchNode._make([Vec3(0,0,0),Quat(),R0,_uvScale])] # initial node      # make a starting node flat at 0,0,0
    trunk = thisBranch
    for b in range(3):
        L=L0 *lfact**b
        if b== 0:
            maxA = 5.0 # trunk
        else:
            maxA = int(200.0 / L) # branchs
            thisBranch = [trunk[b]]# test just walk up 1 node of trunk and start over
        for i in range(1,numGens+1):
#            print [x.quat for x in thisBranch] # DEBUG        
            curQ = thisBranch[i-1].quat
            curP = thisBranch[i-1].pos
            # make a new point w.r.t. the current
            quat = Quat()
            quat.setHpr(Vec3(0,random.randint(-maxA,maxA),random.randint(-maxA,maxA)))
            quat *= curQ #rotate curQ by newQ and put in newQ
            pos = curP + quat.getUp() * L 
            radius = rfact*thisBranch[i-1].radius
            perim = 2*_polySize*radius*sin(pi/_polySize) # use perimeter to calc texture length/scale
            perim = 1
            
#            IS it better to keep integer U scale around for tiling???
            UVcoord = (_uvScale[0]*perim, thisBranch[i-1].texUV[1] + L*float(_uvScale[1]) ) # This will keep the texture scale per unit length constant
            L *= lfact
            newNode = BranchNode._make([pos,quat,radius,UVcoord])
            thisBranch.append(newNode)        
    
        tree.branchFromNodes(thisBranch[0:])
        if b==0: trunk = thisBranch 
        numGens -= 1

#
#
#    #demonstrate growing
#    _Nstep = 12
#    last = [0] # a bit hacky
#    dt = .01
#    def grow(task):
#        if task.time > last[0] + dt:
#            t.grow(removeLeaves=1,leavesScale=1.0,trunkRate = 0)
#            last[0] = task.time
#            #t.leaves.detachNode()
#        if last[0] > _Nstep*dt:
#            print('grow done')
#            t.setScale(1)
#            t.flattenStrong()
#            t.write_bam_file('sampleTree.bam')
#            return task.done
#        return task.cont
#    base.taskMgr.add(grow, "growTask")
    def rotateTree(task):
        phi = 30*task.time
        tree.setH(phi)
        return task.cont
#    base.taskMgr.add(rotateTree,"merrygorouhnd")
    
#    t.grow(_Nstep,removeLeaves=1,leavesScale=1.0,trunkRate = 1.0)
#    base.toggleWireframe()
    base.accept('escape',sys.exit)
    base.accept('z',base.toggleWireframe)
    base.run()