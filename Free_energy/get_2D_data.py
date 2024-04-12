import os
import re
import math
import numpy as np
import pandas as pd
from ase.io import read
import numpy as np

class plot2D():

	#define constructor
	def __init__(self ):
		self.up_pH_limit = 8
		self.pH_step = 1
		self.qe = 1.60217663*10**(-19)
		self.to_eV = 6.24150907*10**(18) #1 Coulb * Volt = 6.24150907*10**(18) eV
		self.T = 300
		self.kB = 8.617333262 * 10**(-5)
		self.ln10KT = self.T * self.kB * math.log(10) 
		self.loc = os.getcwd()
		self.values = self.get_omega()

	def get_number_of_H( self, struc ):
		l = [ atom.index for atom in struc if atom.symbol == "H" ] 
		return len(l)

	def get_omega_H2( self ):
		os.chdir( self.loc + "/H2")
		word = "GC Correction"
		struc = read( "OUTCAR" )
		with open( "OUTCAR", "r" )  as file:
			for line_number, line in enumerate( file ):
				if word in line:
					a = line
		correction = re.findall(r'[-+]?\d*\.\d+|\d+', a)
		correction = float(".".join(correction))
		return struc.get_potential_energy() - correction
	
	def transform_keys_to_coverage( self, keys_list ):
		systems = list()
		for i in keys_list:
			if i.startswith("1x1x6"):
				systems.append("1ML")
			elif i.startswith("2x2x6"):
				systems.append("1/4ML")
			elif i.startswith("3x3x6"):
				systems.append("1/9ML")
			elif i.startswith("4x4x6"):
				systems.append("1/16ML")
		return systems
	
	def get_omega( self ):
		energy = {}
		energy_diff = {}
		for i in ["clean_Bi", "H_Bi"]:
			for j in ["chg_0.0",  "chg_-0.5",  "chg_-1.0",  "chg_-1.5",  "chg_-2.0", "chg_-2.5"]:
				for k in ["1x1x6", "2x2x6", "3x3x6", "4x4x6"]:
					os.chdir( self.loc + "/" + i + "/" + j + "/" + "target_potential" + "/" + k )
					struc = read( "OUTCAR" )
					energy[str(i) + "_" +  str(j) + "_" + str(k)] = struc.get_potential_energy()					
		for i in ["1x1x6", "2x2x6", "3x3x6", "4x4x6"]:
			for j in ["0.0",  "-0.5",  "-1.0",  "-1.5",  "-2.0", "-2.5"]:
				energy_diff[i + "_" + "chg_" + j + "_side"] = energy["H_Bi_" + "chg_"+ j + "_" + i] - energy["clean_Bi_" + "chg_" + j + "_" + i] - 0.5* self.get_omega_H2() 
		return energy_diff

	def get_data_dictionary( self ):
		energy_diff_pH = {}
		for i in ["1x1x6", "2x2x6", "3x3x6", "4x4x6"]:
			for j in ["0.0",  "-0.5",  "-1.0",  "-1.5",  "-2.0", "-2.5"]:
				for pH in range(0, self.up_pH_limit, self.pH_step ):
					energy_diff_pH[ i + "_" + "chg_" + j + "_pH_" + str(pH) ] = self.values[ i + "_" + "chg_" + j + "_side" ] + self.ln10KT * pH - float( j )
		return energy_diff_pH

	def get_min_omega(self, dictionary, voltage , pH):
		min_val = math.inf
		for system in [ "1x1x6", "2x2x6", "3x3x6", "4x4x6" ]:
			current_key = str( system ) + "_" + "chg_" + voltage + "_pH_" + str(pH)
			#print(current_key + ": ", dictionary[ current_key ])
			if dictionary[ current_key ] < min_val:
				min_val = dictionary[ current_key ]
				key = current_key
		#print("The system with the lowest energy is:", key, "and has Omega =", round(min_val, 4))
		return key, min_val

	def get_data_as_DataFrame( self, pH ):
		data = {}
		df = pd.DataFrame()
		omegas = list()
		keys = list()
		dictionary = self.get_data_dictionary()
		df["V"] = df["pH"] = df["Coverage"] = df["Omega"] = np.nan
		V = [ "0.0", "-0.5", "-1.0", "-1.5", "-2.0", "-2.5" ]
		pH_list = [ str(pH) for i in range(0, len(V) ) ]
		ener = self.get_data_dictionary()
		df["pH"] = pH_list
		df["V"] = V
		for i in V:
			key, omega = self.get_min_omega( dictionary, i , pH)	
			omegas.append( omega )
			keys.append( key )
			#print("----" * 20)
		keys =  self.transform_keys_to_coverage( keys )
		df["Coverage"] = keys
		df["Omega"] = omegas
		return df

	def get_all_data_in_dictionary(self):
		data = {}
		all_dfs = []	
		for pH in range(0, self.up_pH_limit):
			df = self.get_data_as_DataFrame(pH=pH)
			data["pH=" + str(pH)] = df
			all_dfs.append(df)
		#print( all_dfs  )		
		#for key, value in data.items():
		#	print(key, value)
		#	print("---" * 10)
		return data


class fix_data():
	
	def __init__( self ):
		obj = plot2D()	
		self.dictionary = obj.get_all_data_in_dictionary()

	def get_pH( self ):
		pH = list()
		for i in self.dictionary.keys():
			pH_number = re.findall(r'\d+', i)[0]
			pH.append( int( pH_number) )		
		pH = np.arange( min(pH), max(pH) + 1 )
		return pH


	def get_voltages( self ):
		voltage = list()
		key = list( self.dictionary.keys() )[0]  
		for i in self.dictionary[ key ]["V"]:
			voltage.append(  float( i )  )
		return voltage

	def get_coverages( self ):
		c = {}
		count = 0
		for i in self.dictionary.keys():
			cov = list()
			for j in self.dictionary[ i ]["Coverage"]:
				num = int( re.findall(r'\d+', j)[ 0 ] ) / int (re.findall(r'\d+', j)[ 1 ] )
				cov.append( num )
			c["c" + str( count ) ] = np.array( [ cov ] )
			count += 1
		Z = np.array([ c[ i ] for i in c.keys()  ])
		return Z

	
if __name__ == "__main__":		
	obj = plot2D()	
	
	d = obj.get_all_data_in_dictionary()
	for key, value in d.items():
		print(key)
		print(value)
