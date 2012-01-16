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

from direct.showbase.ShowBase import ShowBase
from panda3d.core import NodePath, Geom, GeomNode, GeomVertexArrayFormat, TransformState, GeomVertexWriter, GeomTristrips, GeomVertexRewriter, GeomVertexReader, GeomVertexData, GeomVertexFormat, InternalName
from panda3d.core import Mat4, Vec3, CollisionNode, CollisionTube, Point3, Quat
from math import sin,cos,pi
import random
from collections import namedtuple

#from panda3d.core import PStatClient
#PStatClient.connect()

_polySize =8

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
        #0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
#         newCs.setRow(0, vecList[2]) #right
#         newCs.setRow(1, vecList[1]) #up
#         newCs.setRow(2, vecList[0]) #forward
#         newCs.setRow(3, Vec3(0, 0, 0))
#         newCs.setCol(3, Vec4(0, 0, 0, 1))   
        newCs = Mat4()
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
FractalTree.makeFMT()


class flexTree(FractalTree):
    def __init__(self):       
        self.bodydata = GeomVertexData("body vertices", GeomVertexFormat.getV3n3t2(), Geom.UHStatic)

#        if maxAngle: self.maxAngle = maxAngle
#        if maxBend: self.maxBend = maxBend
        barkTexture = base.loader.loadTexture(_BarkTex_)
        leafModel = base.loader.loadModel(_LeafModel)
        leafModel.clearModelNodes()
        leafModel.flattenStrong()
        leafTexture = base.loader.loadTexture(_LeafTex_)
        leafModel.setTexture(leafTexture, 1) 
        leafModel.setScale(0.1)
        leafModel.setTransparency(1)

        FractalTree.__init__(self, barkTexture, leafModel, [1], [1], [1])

    #this draws the body of the tree. This draws a ring of vertices and connects the rings with
    #triangles to form the body.
    #this keepDrawing paramter tells the function wheter or not we're at an end
    #if the vertices before you were an end, dont draw branches to it
    def drawBody(self, pos, quat, radius=1,UVcoord=(1,1), isRoot=False, numVertices=_polySize):
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
            currAngle += angleSlice 
        
        #we cant draw quads directly so we use Tristrips
        if (startRow != 0):
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
        newCs = Mat4()
        quat.extractToMatrix(newCs)
        axisAdj = Mat4.scaleMat(scale) * newCs * Mat4.translateMat(pos)       
        leafModel = NodePath("leaf")
        self.leafModel.instanceTo(leafModel)
        leafModel.reparentTo(self.leaves)
        leafModel.setTransform(TransformState.makeMat(axisAdj))
        
    def addBranch(self, rootNode,  angFunc, aParam, radFunc, rParam, lfact):
        # defines a "branch" as a list of BranchNodes and then
        # calls branchfromNodes
        
        #12.27 new approach for start: 
            # take rootNode pos, assign NEW branch radius as start
            # Rotate new rootNode heading to populate around the tree/branch            
            # rotate new rootNode to match second Node angle
            
            # other notes: a tree cares about absolute "up" and left and right are
            # relateive to abs "up" cross product branches "up" (forward along the branch)
            
        pos,radius,L,quat,UV = rootNode
#        radius = rfact*radius # SHOULD BE radFunc CALL HERE
        adj = Quat()
        adj.setHpr(Vec3(90,90,0))
        quat *= adj
        prevNode = BranchNode._make([pos,radius,L,quat,UV])
        thisBranch = [prevNode] # start new branch list with newly created rootNode
        for i in range(1,numSegs+1): # start a 1, 0 is root node, now previous
            # make a new point w.r.t. the current
            quat = angFunc(prevNode.quat,**aParam)#rotate curQ by newQ and put in newQ
            
            pos = prevNode.pos + quat.getUp() * L 
            radius = radFunc(prevNode,**rParam)
#            perim = 2*_polySize*radius*sin(pi/_polySize) # use perimeter to calc texture length/scale
            perim = 1 # integer tiling of uScale
            
            UVcoord = (_uvScale[0]*perim, prevNode.texUV[1] + L*float(_uvScale[1]) ) # This will keep the texture scale per unit length constant
            L *= lfact
            newNode = BranchNode._make([pos,radius,L,quat,UVcoord])
            thisBranch.append(newNode)
            prevNode = newNode # this is now the starting point on the next iteration
        self.branchFromNodes(thisBranch) 
        return thisBranch
        
    def branchFromNodes(self,nodeList): # draws the actual geometry
        # sends the BranchNode list to the drawBody function to generate the 
        # actual geometry
#        endNode = nodeList.pop() # need to set keepDraw False on last node
        for i,node in enumerate(nodeList):
            if i == 0: isRoot = True
            else: isRoot = False
#            if i == len(nodeList)-1: keepDrawing = True
#            else: 
            self.drawBody(node.pos, node.quat, node.radius,node.texUV,isRoot)
            if i==len(nodeList)-1 and _DoLeaves: self.drawLeaf(node.pos,node.quat,_LeafScale)
#        self.drawBody(endNode.pos,endNode.quat,endNode.radius,endNode.texUV,keepDrawing=1) # tell drawBody this is the end of the branch

def AngleFunc(curQuat,*args,**kwargs):
    # Takes current quaterion and list of kwargs
    # returns a new quaterion by what ever function
    # you want to define in here
    # (i.e. overload this method)
    
    # My method: per some reading, trees want maximum cross section to the sun
    # branches  tend to spread outwards from the trunk / parent branch
    # tips of branches tend to be higher (upward) from the rest of the branch
    
    quat = Quat()
#    maxA = min(kwargs['absLim'], int(kwargs['Ldiv'] / kwargs['length'])) # branchs
    H0 = kwargs['H']
    dh = kwargs['dh']
    P0 = kwargs['P']
    dp = kwargs['dp']
    R0 = kwargs['R']
    dr = kwargs['dr']
    
#    quat.setHpr(Vec3(random.randint(-180, 180)*0, 0*random.randint(-maxA,maxA),random.randint(maxA,maxA)))
    quat.setHpr(Vec3(H0 + random.randint(-dh, dh), P0+random.randint(-dp,dp),R0 + random.randint(-dr,dr)))
    if _relAng:
        quat *= curQuat # this applies a  relative change. Otherwise, quat is absolute(?)
    return quat

def RadiusFunc(curNode,*args,**kwargs):
    rfact = kwargs['rfact']
    return rfact*curNode.radius

BranchNode = namedtuple('BranchNode','pos radius len quat texUV') # len is TO next node (delta pos vectors)

if __name__ == "__main__":
#    random.seed(11*math.pi)
    L0 = 2.0 # initial length
    R0 = 1.0 #initial radius
    Rf = .10 # final radius
    numGens = 2
    numSegs = 2 # number of nodes per branch; 2 ends and n-2 body nodes
    lfact = .85
    rfact = (Rf/R0)**(1.0/numSegs) # fixed start and end radii
    
    _uvScale = (1,.2) #repeats per unit length (around perimeter, along the tree axis) 
    _BarkTex_ = "../resources/models/barkTexture.jpg"
    _LeafTex_ = '../resources/models/material-10-cl.png'
    _LeafModel = '../resources/models/shrubbery'
    _LeafScale = .125
    _DoLeaves = 1
    _relAng = 0    # ang function is a relative adjustment if true. absolute orientation otherwise
    
    base = ShowBase()
    base.cam.setPos(0, -30, 5)
    base.setFrameRateMeter(1)
    tree = flexTree()
    tree.setTwoSided(1)    
    tree.reparentTo(base.render)
    
#TODO: make parameters: lfact, rfact, and angle picking, point to functions that 
# take a function that will define the result of each
    root = BranchNode._make([Vec3(0,0,0),R0,L0,Quat(),_uvScale]) # initial node      # make a starting node flat at 0,0,0
#    Aparams = {'absLim':0,'Ldiv':90.0,'length':L} 
    Aparams = {'H':0,'dh':0,'P':0,'dp':5,'R':0,'dr':0}  
    Rparams = {'rfact':rfact}
    trunk = tree.addBranch(root, AngleFunc, Aparams, RadiusFunc, Rparams, lfact)
    children = trunk[1:-2] # each node in the trunk will span a branch
    nextChildren = [] 
    while numGens>0:
        for root in children:
#            Aparams = {'absLim':45,'Ldiv':90.0,'length':L}   
            Aparams = {'H':0,'dh':0,'P':67,'dp':23,'R':0,'dr':0}
            curBr = tree.addBranch(root, AngleFunc, Aparams, RadiusFunc, Rparams, lfact) # return the current branch node list
            nextChildren += curBr
            
        # IMPLEMENT A "SELECT CHILDREN" FUNC SO NOT ALL NODES ARE BRANCHES
        # CAN ALSO DUPLICATE NODES FOR MULTIPLE BRANCHES PER NODE
        children = nextChildren
        nextChildren = []
        numGens -= 1
            
    tree.flattenStrong()

    def rotateTree(task):
        phi = 30*task.time
        tree.setH(phi)
        return task.cont
    base.taskMgr.add(rotateTree,"merrygoround")
    
#    base.toggleWireframe()
    base.accept('escape',sys.exit)
    base.accept('z',base.toggleWireframe)
    base.run()