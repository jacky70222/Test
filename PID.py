#-*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import time
import thread
import threading
import random
import math
from random import *
import pylab
from pylab import *
import pyghmi.ipmi.private.session as ipmisession
import Tkinter as tk
from Tkinter import *
from pyghmi.ipmi import command
from pyghmi.ipmi.private import constants
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
import pickle

import matplotlib.pyplot as plt
import numpy as np
import xml.dom
import xml.etree.cElementTree as ET
from xml.etree import ElementTree as etree
from xml.etree.ElementTree import Element, SubElement, ElementTree
from xml.dom import minidom




MaxYaxisValue = 450

windows = tk.Tk()
windows.minsize(500, 300)
IOTFrame = Frame(windows)
IOTFrame.pack()

IPEntry = tk.Entry(IOTFrame)
IPEntry.insert(0, '192.168.22.57')

xAchse=pylab.arange(0,100,1)
yAchse=pylab.array([0]*100)

fig, ax = plt.subplots()
ax.grid(True)
ax.set_title("ADRC")
ax.set_xlabel("Time")
ax.set_ylabel("Temperature/PWM")
ax.axis([0,1000,0,MaxYaxisValue])

line1=ax.plot(xAchse,yAchse, "-r", label="Temperature")
#line2=ax.plot(xAchse,yAchse, "-b", label="Watt")
line3=ax.plot(xAchse,yAchse, "-y", label="PWM")
legend(loc='upper left')


canvas = FigureCanvasTkAgg(fig, master=windows)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

toolbar = NavigationToolbar2TkAgg( canvas, windows )
toolbar.update()
canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

CPUTemperature = []


TemperatureData=[]
WattDatas=[]
PWMDatas=[]






response = {}


Start = True


UpdateFlag = False
mutex = threading.Lock()





def prettify(root):
	rough_string = ET.tostring(root, 'utf-8')
	reparsed = minidom.parseString(rough_string)
	return reparsed.toprettyxml(indent="\t")


def RealtimePloter():
	global CPUTemperature, WattDatas, PWMDatas, Start
	
	
	if len(CPUTemperature) == 0:
		CurrentXAxis=pylab.arange(0,2,1)
	else:
		CurrentXAxis=pylab.arange(0,len(CPUTemperature),1)
	
	if len(CPUTemperature) > 0:
		line1[0].set_data(CurrentXAxis,pylab.array(CPUTemperature[-len(CPUTemperature):]))
		#line2[0].set_data(CurrentXAxis,pylab.array(WattDatas[-len(WattDatas):]))
		line3[0].set_data(CurrentXAxis,pylab.array(PWMDatas[-len(PWMDatas):]))
			
	
	
	if CurrentXAxis.max() == 0:
		ax.axis([0,1,0,MaxYaxisValue])
	else:
		ax.axis([CurrentXAxis.min(),CurrentXAxis.max(),0,MaxYaxisValue])

	canvas.draw()
	#windows.after(25,RealtimePloter)
	


def GetSensorReading(ipmisession, SensorNum):
	Temp = 0
	response = ipmisession.raw_command(command=0x2D, data=[SensorNum], netfn=0x04)
	
	if response['code'] == 0:
		Temp = response['data'][0]
		
			
		return Temp
	else:
		#print("Get sensor(%x) data error:%x\n" % (SensorNum, response['code']))
		#print Temp
		return 0



class FanControl:
	def __init__(self):
		self.PWM = 0
		self.PWM_ADRC = 0
		self.WhichSensorControl = 0
		self.eTemperature = 0
		self.eTemp = 0
		self.eTemp_1 = 0
		self.error = 0
		self.error_1 = 0
		self.MaxTemp = 0
		self.MaxTemp_1 = 0
		self.eDist = 0
		self.eDist_1 = 0
		self.MaxError = 0
		self.MaxTempSensorNumber = 0
		self.KP = 0
		self.KI = 0
		self.KD = 0
		self.KIIntegration = 0
		self.Delta = 0
		self.KDTimer = 0


class ADRC:
	def __init__(self):
		self.MinimumPWM = -1 * 20
		self.SetPointOfSensor = [0] * 256
		self.KP = [0] * 256
		self.KI = [0] * 256
		self.KD = [0] * 256
		self.k1 = [0] * 256
		self.k2 = [0] * 256
		self.b0 = [0] * 256
		self.xi = [0] * 256
		self.OmegaC = [0] * 256
		self.Omega0 = [0] * 256
		self.FanSettingOfSensor = [0] * 256
		self.Fan = []
		for i in range(0, 7):
			fan = FanControl()
			self.Fan.append(fan)
			
		tree = ET.ElementTree(file='SensorSetting.xml')
		root = tree.getroot()
		for SensorSetting in root:
			for Sensor in SensorSetting:
				SensorNumber = 0
				SetPoint = 0
				AllFanSetting = 0
				for data in Sensor:
					if cmp(data.tag,"SensorNumber") == 0:
						SensorNumber = int(data.text)
					
					if cmp(data.tag,"SetPoint") == 0:
						SetPoint = int(data.text)
					
					if cmp(data.tag,"P") == 0:
						KP = float(data.text)
						self.KP[SensorNumber] = KP
					
					if cmp(data.tag,"I") == 0:
						KI = float(data.text)
						self.KI[SensorNumber] = KI
						
					if cmp(data.tag,"D") == 0:
						KD = float(data.text)
						self.KD[SensorNumber] = KD
					
					if cmp(data.tag,"k1") == 0:
						self.k1[SensorNumber] = float(data.text)
					
					if cmp(data.tag,"k2") == 0:
						self.k2[SensorNumber] = float(data.text)
					
					if cmp(data.tag,"b0") == 0:
						self.b0[SensorNumber] = float(data.text)
					
					if cmp(data.tag,"xi") == 0:
						self.xi[SensorNumber] = float(data.text)

					if cmp(data.tag,"OmegaC") == 0:
						self.OmegaC[SensorNumber] = float(data.text)
					
					if cmp(data.tag,"Omega0") == 0:
						self.Omega0[SensorNumber] = float(data.text)
					
					if cmp(data.tag,"FAN1") == 0:
						if int(data.text) == 1:
							AllFanSetting = AllFanSetting | 0x01
						
					if cmp(data.tag,"FAN2") == 0:
						if int(data.text) == 1:
							AllFanSetting = AllFanSetting | 0x02
						
					if cmp(data.tag,"FAN3") == 0:
						if int(data.text) == 1:
							AllFanSetting = AllFanSetting | 0x04
						
					if cmp(data.tag,"FAN4") == 0:
						if int(data.text) == 1:
							AllFanSetting = AllFanSetting | 0x08
							
					if cmp(data.tag,"FAN5") == 0:
						if int(data.text) == 1:
							AllFanSetting = AllFanSetting | 0x10
							
					if cmp(data.tag,"FAN6") == 0:
						if int(data.text) == 1:
							AllFanSetting = AllFanSetting | 0x20
							
					if cmp(data.tag,"FAN7") == 0:
						if int(data.text) == 1:
							AllFanSetting = AllFanSetting | 0x40
				
				self.SetPointOfSensor[SensorNumber] = SetPoint
				self.FanSettingOfSensor[SensorNumber] = AllFanSetting



	def PWMControl(self, ipmisession, FanNum, PWM):
		FinalPWM = -1 * PWM
		if FinalPWM > 255:
			FinalPWM = 255
		
		if FinalPWM < 0:
			FinalPWM = 0
		
		if FinalPWM >= 0:
			response = ipmisession.raw_command(netfn=0x3A,command=0x19,data=[0x00, FanNum + 6, int(FinalPWM)])
	
		return FinalPWM


	


		
	def Run(self, ipmisession):
		global CPUTemperature, WattDatas, PWMDatas, Start
		FirstRunFlag = True
		TempError = 0
		MaxError = 0
		MaxErrorSensorNumber = [0] * 7
		tempu = 0
		e = [0] * 7
		eInt = [0] * 7
		eDer = [0] * 7
		e_1 = [0] * 7
		eInt_1 = [0] * 7
		eDer_1 = [0] * 7
		
		u0 = [0] * 7
		u = [0] * 7
		u_1 = [0] * 7
		z1 = [0] * 7
		z2 = [0] * 7
		
		z1_1 = [0] * 7
		z2_1 = [0] * 7
		SensorNumber = 0
		GetTemperatureFlag = [0] * 256
		TemperatureOfSensor = [0] * 256
		sampleTime = 0.25
		filterCoefficient = 10
		TempMax = 0
		PWMMax = 0
		e1 = 0
		Run = False
		mutex.acquire()
		Run = Start
		mutex.release()

		print("Temp32,PWM(0),z1(0),z2(0),Temp33,PWM(6),z1(6),z2(6)")
		
		while Run:
			iterationStartTime = time.time()

			for FanID in range(0, 7):
				bit = 0x01 << FanID
				MaxError = 0
				TempMax = 0
				MaxErrorSensorNumber[FanID] = 0
				for SensorNumber in range(256):
					if (self.FanSettingOfSensor[SensorNumber] & bit) > 0:
						if GetTemperatureFlag[SensorNumber] == 0:
							TemperatureOfSensor[SensorNumber] = GetSensorReading(ipmisession,SensorNumber)
							GetTemperatureFlag[SensorNumber] = 1
						TempError = self.SetPointOfSensor[SensorNumber] - TemperatureOfSensor[SensorNumber]
						if TempError <= MaxError:
							if TempError < MaxError:
								self.Fan[FanID].WhichSensorControl = SensorNumber
							else:
								#Search the maximum temperature, and use this temperature to control PWM
								if TemperatureOfSensor[SensorNumber] > TemperatureOfSensor[MaxErrorSensorNumber[FanID]]:
									self.Fan[FanID].WhichSensorControl = SensorNumber
						else:
							if MaxError == 0:
								MaxError = TempError
								MaxErrorSensorNumber[FanID] = SensorNumber
								self.Fan[FanID].MaxError = TempError
								self.Fan[FanID].WhichSensorControl = SensorNumber
						if self.Fan[FanID].WhichSensorControl == SensorNumber:
							if TempError <= MaxError:
								MaxError = TempError
								MaxErrorSensorNumber[FanID] = SensorNumber
								self.Fan[FanID].MaxError = TempError
							self.Fan[FanID].error = TempError
							self.Fan[FanID].eTemperature = TemperatureOfSensor[SensorNumber]
							self.Fan[FanID].KP = self.KP[SensorNumber]
			GetTemperatureFlag = [0] * 256
			MaxErrorSensorNumber = [0] * 7
			
			
			for FanID in range(0, 7):
				if self.Fan[FanID].WhichSensorControl != 0:
					SensorNumber = self.Fan[FanID].WhichSensorControl

					if self.KP[SensorNumber] != 0:
						#PID
						#  //   a     = filter corner freq (rad/sec)   filterCoefficient
						#  //   T     = sample time   sampleTime
						#  //   e(n)  = target error
						#  //   x1(n) = e(n)                                                  proportional
						#  //   x2(n) = x2(n-1) + e(n-1) * T                                  integral
						#  //   x3(n) = x3(n-1) + N/(N T +1) (e(n) - e(n-1)) MATLAB
						e[FanID]    = float(self.SetPointOfSensor[SensorNumber]) - TemperatureOfSensor[SensorNumber]
						
						if( (u_1[FanID] > -255 and e_1[FanID] < 0) or (u_1[FanID] < self.MinimumPWM and e_1[FanID] > 0) ):	
							eInt[FanID] = eInt_1[FanID] + e_1[FanID] * sampleTime
						else:
							eInt[FanID] = eInt_1[FanID]
							
						eDer[FanID] = eDer_1[FanID] + filterCoefficient / (filterCoefficient*sampleTime+1) * (e[FanID] - e_1[FanID])
						u[FanID] = self.KP[SensorNumber] * e[FanID] + self.KI[SensorNumber] * eInt[FanID] + self.KD[SensorNumber] * eDer[FanID] 
						# /PID
					else:
						# ADRC
						beta = np.exp(-self.Omega0[SensorNumber] * sampleTime)
						kp = self.OmegaC[SensorNumber]
						l1 = 1 - beta**2
						l2 = ((1 - beta)**2)/sampleTime

						z1[FanID]=(-l1*sampleTime+1)* z1_1[FanID] + sampleTime*z2_1[FanID] + l1*sampleTime*TemperatureOfSensor[SensorNumber] + self.b0[SensorNumber]*sampleTime*u_1[FanID]
						z2[FanID]=(-l2*sampleTime)  * z1_1[FanID] +            z2_1[FanID] + l2*sampleTime*TemperatureOfSensor[SensorNumber]
						
						u0[FanID] = kp * ( float(self.SetPointOfSensor[SensorNumber]) - TemperatureOfSensor[SensorNumber] )
#						u0[FanID] = kp * ( float(self.SetPointOfSensor[SensorNumber]) - z1[FanID] )
						u[FanID] = (u0[FanID] - z2[FanID])/self.b0[SensorNumber]
						# /ADRC
					
					
					self.Fan[FanID].PWM_ADRC = u[FanID]
					
					if self.Fan[FanID].PWM_ADRC <= -255:
						self.Fan[FanID].PWM_ADRC = -255
					if self.Fan[FanID].PWM_ADRC >= self.MinimumPWM:
						self.Fan[FanID].PWM_ADRC = self.MinimumPWM
						
					self.Fan[FanID].PWM = self.PWMControl(ipmisession, FanID, self.Fan[FanID].PWM_ADRC)
					
					# if self.KP[SensorNumber] == 0:
						# try:
							# print("CPUTemp(%x):%f u0:%f u[%d]:%f z1[%d]:%f z2:%f PWM%d:%d, ADRC_PWM:%f kp:%f l1:%f l2:%f\n" % (self.Fan[FanID].WhichSensorControl, TemperatureOfSensor[SensorNumber], u0[FanID], FanID, u[FanID], FanID, z1[FanID], z2[FanID], FanID, self.Fan[FanID].PWM, self.Fan[FanID].PWM_ADRC, kp, l1, l2))
							
						# except Exception as err:
							# print("%s" % err)

					e_1[FanID]    = e[FanID]
					eInt_1[FanID] = eInt[FanID]
					eDer_1[FanID] = eDer[FanID]
						
					z1_1[FanID] = z1[FanID]
					z2_1[FanID] = z2[FanID]
#					z3_1[FanID] = z3[FanID]
#					u_1[FanID] = u[FanID]
					u_1[FanID] = self.Fan[FanID].PWM_ADRC
					
			print("%f,%f,%f,%f,%f,%f,%f,%f" % 
				(TemperatureOfSensor[32], self.Fan[0].PWM, z1[0], z2[0], TemperatureOfSensor[33], self.Fan[6].PWM, z1[6], z2[6])
			)			
			
			#Find out the maximum PWM and temperature value
			PWMMax = 0
			TempMax = 0
			for FanID in range(0, 7):
				if TempMax < self.Fan[FanID].eTemperature and self.Fan[FanID].WhichSensorControl != 0:
					TempMax = self.Fan[FanID].eTemperature
				if PWMMax < self.Fan[FanID].PWM and self.Fan[FanID].WhichSensorControl != 0:
					PWMMax = self.Fan[FanID].PWM
				
				
			Title = "Temperature:%f PWM:%f\n" % (TempMax, PWMMax)
			mutex.acquire()
			Run = Start
			mutex.release()
			if Run == False:
				Title = "Exit program"
			ax.set_title(Title)
			CPUTemperature.append(TempMax)
			#WattDatas.append(Watt)
			PWMDatas.append((float(PWMMax)/255.0) * 100)
			
			windows.after(25,RealtimePloter)	

#			print("Time: %f\n" % time.time())  <- has decimal seconds
#			print("Remaining time: %f\n" % (iterationStartTime + sampleTime - time.time()))
#			time.sleep(sampleTime)
			while 1:
				if time.time() > iterationStartTime + sampleTime:
					
					break



def StartThread(IPAddress):
	#IPAddress = IPEntry.get()
	#print("ip:%s" % IPAddress)
	IPMISession = ipmisession.Session(bmc=IPAddress,userid="admin",password="admin")
	adrc = ADRC() 
	adrc.Run(IPMISession)
	
def Start(SensorNum, IPAddress):
	pid = threading.Thread(target=StartThread, args=(IPAddress,))
	pid.start()

	
	return


def Stop(SensorNum):
	global CPUTemperature, Start, FileName
	
	mutex.acquire()
	Start = False
	
	mutex.release()
	
	#if Start == False:
		#print("Exit program!\n")
	return

			
		


TitleLabel = Label(IOTFrame, width = 10, text="ADRC bata version 0.1")
TitleLabel.pack(side = 'top',fill ='x', pady = 1)

IPLabel = tk.Label(IOTFrame, text="BMC IP address")




IPAddress = IPEntry.get()

#print("ip:%s" % IPAddress)



button = tk.Button(windows, text="Start", command=lambda:Start(0x20, IPAddress))
StopButton = tk.Button(windows, text="Stop", command=lambda:Stop(0x20))
IPLabel.pack(side='left')
IPEntry.pack(side='left')

IPLabel.pack(side='left')
IPEntry.pack(side='left')



button.pack(side='left')
StopButton.pack(side='left')


#windows.after(100,RealtimePloter)


WindowsGUI = threading.Thread(target=windows.mainloop()) 
WindowsGUI.start()
