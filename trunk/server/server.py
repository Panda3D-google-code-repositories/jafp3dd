# -*- coding: utf-8 -*-
"""
Created on Mon Nov 28 13:24:03 2011

@author: us997259
"""

import time,random
from direct.showbase.ShowBase import taskMgr, ShowBase
from direct.showbase.DirectObject import DirectObject
#import direct.directbase.DirectStart
from panda3d.core import *
import rencode

class serverNPC(NodePath):
# Data needed to sync: x,y,z,h,p,r,speed
    nextUpdate = 0
    speed = 0

    def makeChange(self,ttime):
        self.speed = 10*abs(random.gauss(0,.33333))
        newH = random.gauss(0,60)
        self.setH(self,newH) #key input steer
        self.nextUpdate = ttime + 5*random.random() # randomize when to update next

class ServerApp(DirectObject):
    def __init__(self):
        DirectObject.__init__(self)
        print "Starting the world..."
        port_address = 9099
        backlog = 1000
        self.activeConnections = []

        print "Starting up Server Network Managers..."
        self.cManager = QueuedConnectionManager()
        self.cListener = QueuedConnectionListener(self.cManager,0)
        self.cReader = QueuedConnectionReader(self.cManager,0)
        self.cWriter = ConnectionWriter(self.cManager,0)

        tcpSocket = self.cManager.openTCPServerRendezvous(port_address,backlog)
        self.cListener.addConnection(tcpSocket)
        print "Server Adding pollers..."
        taskMgr.add(self.tskListenerPolling,'Poll connection listener',-39)
        taskMgr.add(self.tskReaderPolling,'Poll connection reader',-40)
        taskMgr.add(self.tskCheckConnect,'Check for lost connections',-41)
        print "Server Initialization completed successfully!"

    def tskListenerPolling(self,task):
#        for con in self.activeConnections:
#            if not self.cListener.isConnectionOk(con):
#                self.cListener.removeConnection(con)
#                self.activeConnections.remove(con)
#                print "lost connection"

        if self.cListener.newConnectionAvailable():
            rendezvous = PointerToConnection()
            netAddress = NetAddress()
            newConnection = PointerToConnection()

            if self.cListener.getNewConnection(rendezvous,netAddress, newConnection):
                newConnection = newConnection.p()
                self.activeConnections.append(newConnection)
                self.cReader.addConnection(newConnection)
            print "Open Connections: %d" % (len(self.activeConnections))
        return task.cont

    def tskReaderPolling(self,task):
        if self.cReader.dataAvailable():
            datagram = NetDatagram()
            #Note that the QueuedConnectionReader retrieves data from all clients
            #connected to the server. The NetDatagram can be queried using
            #NetDatagram.getConnection to determine which client sent the message.

            # check return value incase other thread grabbed data first
            if self.cReader.getData(datagram):
                self.ProcessData(datagram)
        return task.cont

    def tskCheckConnect(self,task):
        if self.cManager.resetConnectionAvailable() == True:
            ptc = PointerToConnection()
            self.cManager.getResetConnection(ptc)
            con = ptc.p()
          
            if con in self.activeConnections:
                self.activeConnections.remove(con)
                print self.activeConnections
            print "CS: Client disconnected" ,con
            self.cManager.closeConnection(con)
        return task.cont
        
    def write(self,messageID, data, connection=None):
        # a none entry results in a broadcast to all active clients
        if not connection: connection = self.activeConnections
#TODO: SERVER SIDE NEEDS TO KNOW WHERE TO SEND THE MESSAGE
        datagram = NetDatagram()
        datagram.addInt32(messageID)
        datagram.addString(rencode.dumps(data,False))
        self.cWriter.send(datagram, connection)

    def ProcessData(self,NetDatagram):
        pass


class TileServer(ServerApp):
    def __init__(self):
        ServerApp.__init__(self)
        self.nextTx = 0
        self.npc = []
        for n in range(10):
            self.npc.append( serverNPC('thisguy'+str(n)))
            self.npc[n].setPos(70,70,0)
        taskMgr.add(self.updateNPCs,'server NPCs')

    def ProcessData(self,datagram):
        t0 = time.ctime()
        I = DatagramIterator(datagram)
        msgID = I.getInt32() # what type of message
        data = rencode.loads(I.getString()) # data matching msgID
        print t0,msgID,data
        if msgID == 10: print data
#            self.write(t0,datagram.getConnection())

    def updateNPCs(self,task):
        dt = task.getDt()
        datagram = NetDatagram()
        data = []
        for iNpc in self.npc:
            if time.time() > iNpc.nextUpdate:         # change direction and heading every so often
                iNpc.makeChange(task.time)
            iNpc.setPos(iNpc,0,iNpc.speed*dt,0) # these are local then relative so it becomes the (R,F,Up) vector
#            poslist.append(iNpc.getPos())
            x,y,z = iNpc.getPos()
            h,p,r = iNpc.getHpr()
#            iNpc.setZ(self.ttMgr.getElevation((x,y)))
#TODO: What to do about terrain heights???

#            for cv in iNpc.getPos():
#                datagram.addFloat32(cv)
#            for cv in iNpc.getHpr():
#                datagram.addFloat32(cv)
#            datagram.addFloat32(iNpc.speed)
            data.append([x,y,z,h,p,r,iNpc.speed])
        # send x,y,z's to client(s)
        if time.time() > self.nextTx:
            for client in self.activeConnections:
                self.write(int(0),data, client) # rencode lets me send objects??
            self.nextTx = time.time() + 1.100
        return task.cont





if __name__ == '__main__':
    server = TileServer()
#    nMgr = NPCmanager()
#    server.run()
    taskMgr.run()


