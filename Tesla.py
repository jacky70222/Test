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

def Tesla():
	print("Hello world")