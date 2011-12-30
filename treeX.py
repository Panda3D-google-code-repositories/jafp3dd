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
from panda3d.core import Mat4, Vec4, Vec3, CollisionNode, CollisionTube, Point3, Quat
from math import sin,cos,pi, sqrt
import random
from collections import namedtuple
import pdb

#from panda3d.core import PStatClient
#PStatClient.connect()
#import pycallgraph
#pycallgraph.start_trace()

_polySize = 12

class Branch(NodePath):
    def __init__(self, nodeName):
        NodePath.__init__(self, nodeName)
        self.numPrimitives = 0
        self.nodeList = []    # for the branch geometry itself
        self.buds = []        # a list of children. "buds" for next gen of branchs
        self.gen = 0        # ID's generation of this branch (trunk = 0, 1 = primary branches, ...)
        # contains 2 Vec3:[ position, and Hpr]. Nominally these are set by the parent Tree class
        # with it's add children function(s)
        
        self.bodydata = GeomVertexData("body vertices", GeomVertexFormat.getV3n3t2(), Geom.UHStatic)        
        self.bodies = NodePath("Bodies")
        self.bodies.reparentTo(self)
        
        self.coll = self.attachNewNode(CollisionNode("Collision"))       
        self.coll.show()       
        self.coll.reparentTo(self)

    #this draws the body of the tree. This draws a ring of vertices and connects the rings with
    #triangles to form the body.
    #this keepDrawing paramter tells the function wheter or not we're at an end
    #if the vertices before you were an end, dont draw branches to it
    def drawBody(self, pos, quat, radius=1,UVcoord=(1,1), numVertices=_polySize):
#        if isRoot:
#            self.bodydata = GeomVertexData("body vertices", GeomVertexFormat.getV3n3t2(), Geom.UHStatic)
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
       
        #axisAdj=Mat4.rotateMat(45, axis)*Mat4.scaleMat(radius)*Mat4.translateMat(pos)
        perp1 = quat.getRight()
        perp2 = quat.getForward()   
        
#TODO: PROPERLY IMPLEMENT RADIAL NOISE        
        dr = 0.25 # EXPERIMENTAL: ADDING RADIAL NOISE
#        print "Experimental noise off"
        #vertex information is written here
        angleSlice = 2 * pi / numVertices
        currAngle = 0
        for i in xrange(numVertices+1): 
            adjCircle = pos + (perp1 * cos(currAngle) + perp2 * sin(currAngle)) * radius * (.5+dr*random.random())
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
            return circleGeomNode
        
    def generate(self, pParam, rParam):
        # defines a "branch" as a list of BranchNodes and then calls branchfromNodes
        # Creates a scaled length,width, height geometry to be later
        # otherwise can not maintain UV per unit length (if that's desired)
        # returns non-rotated, unpositioned geom node
        
        
#TODO: MAKE an "addNode" or 
        branchlen = pParam['L']
        branchSegs = pParam['nSegs']
        pParam.update({'iSeg':0})
        rootPos = Vec3(0,0,0) # + self.PositionFunc(**pParam) #add noise to root node; same as others in loop
        rootNode = BranchNode._make([rootPos,rParam['R0'],branchlen,Quat(),_uvScale,0]) # initial node      # make a starting node flat at 0,0,0        
        self.nodeList = [rootNode] # start new branch list with newly created rootNode
        prevNode = rootNode
        
        for i in range(1,branchSegs+1): # start a 1, 0 is root node, now previous
            pParam.update({'iSeg':i})
            newPos = self.PositionFunc(**pParam)
            toVec = newPos - prevNode.pos # point
            dL = prevNode.deltaL + toVec.length() # cumulative length accounts for off axis node lengths
            radius = self.RadiusFunc(position=dL/branchlen,**rParam) # pos.length() wrt to root. if really curvy branch, may want the sum of segment lengths instead..

# MOVE TO UVfunc
#            perim = 2*_polySize*radius*sin(pi/_polySize) # use perimeter to calc texture length/scale
            # if going to use above perim calc, probably want a high number of BranchNodes to minimuze the Ushift at the nodes
            perim = 1 # integer tiling of uScale; looks better; avoids U shifts at nodes     
            UVcoord = (_uvScale[0]*perim, rootNode.texUV[1] + dL*float(_uvScale[1]) ) # This will keep the texture scale per unit length constant
##

            newNode = BranchNode._make([newPos,radius,toVec,rootNode.quat,UVcoord,dL]) # i*Lseg = distance from root
            self.nodeList.append(newNode)
            prevNode = newNode # this is now the starting point on the next iteration

        # sends the BranchNode list to the drawBody function to generate the 
        # actual geometry
        for i,node in enumerate(self.nodeList):
#            if i == 0: isRoot = True
#            else: isRoot = False
#            if i == len(nodeList)-1: keepDrawing = True
#            else: 
            self.drawBody(node.pos, node.quat, node.radius,node.texUV)
        return self.nodeList

    def UVfunc(*args,**kwargs):
        pass # STUB
    def Circumfunc(*args,**kwargs):
        pass # STUB
        
    def PositionFunc(*args,**kwargs):
        upVector = kwargs['upVector']
        iSeg = kwargs['iSeg']
        nAmp = kwargs['Anoise']    
        branchlen = kwargs['L']
        branchSegs = kwargs['nSegs']
    
        Lseg = float(branchlen)/branchSegs
        noise = Vec3(-1+2*random.random(),-1+2*random.random(),0)*nAmp 
        newPos = Vec3(0,0,0) + upVector*Lseg*iSeg  + noise 
        return newPos
        
    def RadiusFunc(*args,**kwargs):
        # radius proportional to length from root of this branch to some power
        rfact = kwargs['rfact']
        relPos = kwargs['position']
        R0 = kwargs['R0']
        newRad = R0*(1 - relPos*rfact) # linear taper Vs length. pretty typical        
        return newRad

class Tree(list):
    branchlist = []

    def lengthFunc(self):
        pass
    
    def __init__(self):
        pass # STUB

    #this draws leafs when we reach an end       
    def drawLeaf(self, pos=Vec3(0, 0, 0), quat=None, scale=0.125):
        #use the vectors that describe the direction the branch grows to make the right
        #rotation matrix
#        newCs = Mat4()
#        quat.extractToMatrix(newCs)
        axisAdj = Mat4.scaleMat(scale) * Mat4.translateMat(pos)       
        leafModel = NodePath("leaf")
        self.leafModel.instanceTo(leafModel)
        leafModel.reparentTo(self.leaves)
        leafModel.setTransform(TransformState.makeMat(axisAdj))

def addNewBuds(branch):
    budPos = budHpr = rad = []
    [gH,gP,gR] = branch.getHpr(base.render) # get global Hpr for later
    for nd in branch.nodeList: # just use nodes for now
        budPos = nd.pos
        rad = .8*nd.radius
        #Child branch Ang func - orient the node after creation
        ang = 90 + random.randint(-23,5)
#        if branch.gen==0:
#            budHpr = Vec3(gH,gP,gR)
        if branch.gen<1: # trunk case
            budHpr = Vec3(random.randint(-180,180),0,ang)
        else:
            side = random.choice((-1,1))
            budHpr = Vec3(gH+side*ang,0,gR)    
        branch.buds.append([budPos,rad,budHpr])
    return branch
    
BranchNode = namedtuple('BranchNode','pos radius toVector quat texUV deltaL') 
# toVector is TO next node (delta of pos vectors)
# deltaL is cumulative distance from the branch root (sum of node lengths)

if __name__ == "__main__":
#    random.seed(11*math.pi)

    # TRUNK AND BRANCH PARAMETERS
    numGens = 2    # number of branch generations to calculate (0=trunk only)
    numSegs = 12 # number of nodes per branch; +1 root = 7 total BranchNodes per branch
    print numGens, numSegs
    _skipChildren = 2 # how many nodes in from the base; including the base, to exclude from children list
    # often skipChildren works best as a function of total lenggth, not just node count
    
    L0 = 5.0 # initial length
    lfact = .6    # length ratio between branch generations
    Lnoise = .1    # percent(0-1) length variation of new branches
    posNoise = 0.1    # noise in The XY plane around the growth axis of a branch
    _UP_ = Vec3(0,0,1) # General axis of the model as a whole
    
    R0 = .5 #initial radius
#    Rf = .1 # final radius
#    rfact = (Rf/R0)**(1.0/numSegs) # fixed start and end radii
    rfact = .95 # taper factor; % reduction in radius between tip and base ends of branch
  
    _uvScale = (1,.4) #repeats per unit length (around perimeter, along the tree axis) 
    _BarkTex_ = "barkTexture.jpg"
#    _BarkTex_ ='./resources/models/barkTexture-1z.jpg'
    

    # LEAF PARAMETERS
    _LeafTex_ = 'Green Leaf.png'
    _LeafModel = 'myLeafModel.x'
    _LeafScale = .75
    _DoLeaves = 0 # not ready for prime time; need to add drawLeaf to Tree Class
 
    base = ShowBase()
    base.cam.setPos(0,-2*L0, L0/2)
#    base.cam.lookAt(base.render)
    base.cam.printHpr()
    
    base.setFrameRateMeter(1)
    bark = base.loader.loadTexture(_BarkTex_)    
    
### GUTS OF "TREE" CLASS
#TODO: make parameters: probably still need a good Lfunc. 
# need angle picking# such that branchs tend to lie flat, slight "up" and out. 
# Distribute branches uniform around radius. 
# "Crown" the trunk; possibly branches. - single point; no rad func and connect all previous nodes to point
# choose "bud" locations other than branch nodes.
# define circumference function (pull out of drawBody())
# 
    Pparams = {'L':L0,'nSegs':numSegs,'Anoise':posNoise*R0,'upVector':_UP_}
    Rparams = {'rfact':rfact,'R0':R0}

    trunk = Branch("Trunk")
    trunk.setTwoSided(1)    
    trunk.reparentTo(base.render)
    trunk.generate(Pparams, Rparams)
    trunk.setTexture(bark)
    trunk = addNewBuds(trunk)

    children = [trunk]*1 # each node in the trunk will span a branch # poor man's multiple branch/node
    nextChildren = []
    leafNodes = []
    for gen in range(1,numGens+1):
        print "Calculating branches..."
        print "Generation: ", gen, " children: ", len(children)
        for thisBranch in children:
            for ib,bud in enumerate(thisBranch.buds[_skipChildren:-1]): # don't include the root
                # Create Child NodePath instance
                newBr = Branch("Branch1") 
                newBr.reparentTo(thisBranch)
#                newBr.setTexture(bark) # If you wanted to do each branch with a unqiue texture
                newBr.gen = gen
                
                # Child branch Radius func 
                Rparams['R0']= bud[1]

                # Child branch position Func
                newBr.setPos(bud[0])                
                lFunc = (L0*lfact**gen)*(1.0-float(ib+1)/numSegs) #branch total length func
                lFunc += lFunc*Lnoise*random.random()
                Pparams['Anoise'] = bud[1]*posNoise    # noise func of tree or branch?
                Pparams.update({'L':lFunc,'nSegs':numSegs+1-gen})

                newBr.setHpr(base.render,bud[2]) 
                
                #Create the actual geometry now
                newBr.generate(Pparams, Rparams)
                newBr = addNewBuds(newBr)
                # Create New Children Function
                nextChildren.append(newBr) 
                # just add this branch to the new Children;
                # use it's nodeList for new children.
                
                
        children = nextChildren # assign Children for the next iteration
        nextChildren = []
#        leafNodes = thisBranch.nodeListleafNodes = thisBranch.nodeList
    #        if gen==numGens-1:2
    
    
    if _DoLeaves:
        print "adding foliage"
        for node in leafNodes:
            trunk.drawLeaf(node.pos,node.quat,_LeafScale)
##############################

    ruler = base.loader.loadModel('./resources/models/plane')
    ruler.setPos(-(R0+.25),0,1) # z = .5 *2scale
    ruler.setScale(.05,1,2) #2 unit tall board
    ruler.setTwoSided(1)
    ruler.reparentTo(base.render)

    # DONE GENERATING. WRITE OUT UNSCALED MODEL
    trunk.setScale(1)        
    trunk.flattenStrong()
    trunk.write_bam_file('./resources/models/sampleTree.bam')
    
    def rotateTree(task):
        phi = 15*task.time
        trunk.setH(phi)
        return task.cont
#    base.taskMgr.add(rotateTree,"merrygoround")
    
#    base.toggleWireframe()
    base.accept('escape',sys.exit)
    base.accept('z',base.toggleWireframe)
#    pycallgraph.make_dot_graph('treeXpcg.png')
    base.run()
