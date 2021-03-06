# -*- coding: utf-8 -*-
"""
Created on Thu Nov 24 19:35:08 2011

@author: shawn
"""

'''
Created on 11.12.2010
Based on Kwasi Mensah's (kmensah@andrew.cmu.edu) "The Fractal Plants Sample Program" from 8/05/2005
@author: Praios

Edited by Craig Macomber

'''
import sys
#import platform
#if platform.system() == 'Windows':
#    sys.path.append('c:\Panda3D-1.7.2')
#    sys.path.append('c:\Panda3D-1.7.2\\bin')

from panda3d.core import NodePath, Geom, GeomNode, GeomVertexArrayFormat, TransformState, GeomVertexWriter, GeomTristrips, GeomVertexRewriter, GeomVertexReader, GeomVertexData, GeomVertexFormat, InternalName
from panda3d.core import Mat4, Vec3, Vec4, CollisionNode, CollisionTube, Point3, Quat
import math, random

#this is for making the tree not too straight
#def _randomBend(inQuat, maxAngle=20):
#    q=Quat()
#    angle=random.random()*2*math.pi
#
#    #power of 2 here makes distrobution even withint a circle
#    # (makes larger bends are more likley as they are further spread)
#    ammount=(random.random()**2)*maxAngle
#    q.setHpr((math.sin(angle)*ammount,math.cos(angle)*ammount,0))
#    return inQuat*q

def _randomBend(inQuat, maxAngle=20):
    q=Quat()
    theta = random.randint(-90,90)
    phi = random.randint(-maxAngle,maxAngle)

    #power of 2 here makes distrobution even withint a circle
    # (makes larger bends are more likley as they are further spread)
#    ammount=(random.random()**2)*maxAngle
    q.setHpr((theta,phi,0))
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
    return _randomBend(quat,20)


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

        self.makeEnds()
        self.makeFromStack(True)
        #self.coll.show()
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
                        #stack.append((newPos, _randomAxis(vecList,3), depth + 1))
                else:
                    #just make another branch connected to this one with a small variation in direction
                    stack.append((newPos, _randomBend(quat, self.maxBend), depth + 1))
            else:
                ends.append((pos, quat, depth))
                self.drawBody(pos, quat, radiusList[depth], False)
                self.drawLeaf(pos, quat)
        self.ends = ends

    def makeColl(self, pos, newPos, radius):
        tube = CollisionTube(Point3(pos), Point3(newPos), radius)
        self.coll.node().addSolid(tube)

    #this draws the body of the tree. This draws a ring of vertices and connects the rings with
    #triangles to form the body.
    #this keepDrawing paramter tells the function wheter or not we're at an end
    #if the vertices before you were an end, dont draw branches to it
    def drawBody(self, pos, quat, radius=1, keepDrawing=True, numVertices=6):
        vdata = self.bodydata
        circleGeom = Geom(vdata)
        vertWriter = GeomVertexWriter(vdata, "vertex")
        #colorWriter = GeomVertexWriter(vdata, "color")
        normalWriter = GeomVertexWriter(vdata, "normal")
        drawReWriter = GeomVertexRewriter(vdata, "drawFlag")
        texReWriter = GeomVertexRewriter(vdata, "texcoord")
        startRow = vdata.getNumRows()
        vertWriter.setRow(startRow)
        #colorWriter.setRow(startRow)
        normalWriter.setRow(startRow)
        sCoord = 0
        if (startRow != 0):
            texReWriter.setRow(startRow - numVertices)
            sCoord = texReWriter.getData2f().getX() + 1
            drawReWriter.setRow(startRow - numVertices)
            if(drawReWriter.getData1f() == False):
                sCoord -= 1
        drawReWriter.setRow(startRow)
        texReWriter.setRow(startRow)

        angleSlice = 2 * math.pi / numVertices
        currAngle = 0
        #axisAdj=Mat4.rotateMat(45, axis)*Mat4.scaleMat(radius)*Mat4.translateMat(pos)
        perp1 = quat.getRight()
        perp2 = quat.getForward()
        #vertex information is written here
        for i in xrange(numVertices+1): #doubles the last vertex to fix UV seam
            adjCircle = pos + (perp1 * math.cos(currAngle) + perp2 * math.sin(currAngle)) * radius
            normal = perp1 * math.cos(currAngle) + perp2 * math.sin(currAngle)
            normalWriter.addData3f(normal)
            vertWriter.addData3f(adjCircle)
            texReWriter.addData2f(1.0*i / numVertices,sCoord)
            #colorWriter.addData4f(0.5, 0.5, 0.5, 1)
            drawReWriter.addData1f(keepDrawing)
            currAngle += angleSlice
        drawReader = GeomVertexReader(vdata, "drawFlag")
        drawReader.setRow(startRow - numVertices)
        #we cant draw quads directly so we use Tristrips
        if (startRow != 0) and (drawReader.getData1f() != False):
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


    def grow(self, num=1, removeLeaves=0, leavesScale=1, trunkRate = 1.0):
        self.iterations += num
        while num > 0:
            self.setScale(self, trunkRate)
            self.leafModel.setScale(self.leafModel, leavesScale / trunkRate )
            if removeLeaves:
                for i,c in enumerate(self.leaves.getChildren()):
#                    print self.numCopiesList[i]
                    c.removeNode()
            self.makeFromStack()
            self.bodies.setTexture(self.barkTexture)
            num -= 1
FractalTree.makeFMT()


class DefaultTree(FractalTree):
    def __init__(self, numIterations=64,branchEvery=20,numBranches=2,maxAngle=None,maxBend=None,lenScale=None):
        if maxAngle: self.maxAngle = maxAngle
        if maxBend: self.maxBend = maxBend
        barkTexture = base.loader.loadTexture("../resources/models/barkTexture.jpg")
        leafModel = base.loader.loadModel('../resources/models/shrubbery')
        leafModel.clearModelNodes()
        leafModel.flattenStrong()
        leafTexture = base.loader.loadTexture('../resources/models/material-10-cl.png')
        leafModel.setTexture(leafTexture, 1)
        leafModel.setScale(0.045)

        lengthList = self.makeLengthList(1, numIterations,lenScale or None)
        numCopiesList = self.makeNumCopiesList(numBranches, branchEvery, numIterations)
        radiusList = self.makeRadiusList(0.25, numIterations, numCopiesList)

        FractalTree.__init__(self, barkTexture, leafModel, lengthList, numCopiesList, radiusList)

    @staticmethod
    def makeRadiusList(radius, iterations, numCopiesList, scale=1.5):
        l = [radius]
        for i in xrange(1, iterations):
            #if i % 3 == 0:
            if i != 1 and numCopiesList[i - 2]:
                radius /= numCopiesList[i - 2] ** 0.5
            else:
                radius /= scale ** (1.0 / 3)
            l.append(radius)
        return l

    @staticmethod
    def makeLengthList(length, iterations, sl=1.0):
        l = [length]
        for i in xrange(1, iterations):
            #if i % 3 == 0:
                #decrease dimensions when we branch
                #length = Vec3(length.getX() / 2, length.getY() / 2, length.getZ() / 1.1)
            length = length / sl
            l.append(length)
        return l

    @staticmethod
    def makeNumCopiesList(numCopies, branchAt, iterations):
        l = list()
        for i in xrange(iterations):
#            if i % int(branchAt) == 0:
            if random.random() <= branchAt:    # go with a probability of a branching occuring
                l.append(random.randint(1,numCopies)) # random of 1 to numCopies branches
            else:
                l.append(0)
        return l

#this grows a tree
if __name__ == "__main__":
#    random.seed(2000*math.pi)
    from direct.showbase.ShowBase import ShowBase
    base = ShowBase()
    base.cam.setPos(0, -20, 2)
#    base.cam.lookAt(base.render)
    base.setFrameRateMeter(1)
    _Nstep = 12
    tree = DefaultTree(numIterations=64,branchEvery=.8,numBranches=3,maxAngle=60, maxBend=20, lenScale = 1.25)
    tree.reparentTo(base.render)
    #make an optimized snapshot of the current tree
#    np = t.getStatic()
#    np.setPos(10, 10, 0)
#    np.reparentTo(base.render)
    #demonstrate growing
    last = [0] # a bit hacky
    dt = .05
    def grow(task):
        if task.time > last[0] + dt:
            tree.grow(removeLeaves=1,leavesScale=1.1,trunkRate = 1.0)
            last[0] = task.time
            #t.leaves.detachNode()
        if last[0] > _Nstep*dt:
            tree.setScale(1)
            tree.flattenStrong()
            tree.writeBamFile('sampleTree.bam')
            return task.done
        return task.cont
    base.taskMgr.add(grow, "growTask")
    base.accept('escape',sys.exit)
    base.setBackgroundColor((.6,.6,1,1))
    base.run()