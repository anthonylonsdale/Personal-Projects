#!/usr/bin/env python

if __name__ == '__main__':
    temperature = 50
    for i in range(1,21):
        temp = int(temperature) * i
        if temp == 1000:
            temp_string = "99_1000"
        else:
            temp_string = str(temp)
        f = open("10x10x10_{}k_moving_py.lmp".format(temp_string), "w+")
        f.write("# bcc iron in a 3d periodic box\n\n")
        f.write("clear\n")
        f.write("units 		metal\n")
        f.write("atom_style 	spin\n\n")
        
        f.write("dimension 	3\n")
        f.write("boundary 	p p p\n\n")
        
        f.write("# necessary for the serial algorithm (sametag)\n")
        f.write("atom_modify 	map array \n\n")
        
        f.write("lattice 	bcc 2.8665\n")
        f.write("region 		box block 0.0 10.0 0.0 10.0 0.0 10.0\n")
        f.write("create_box 	1 box\n")
        f.write("create_atoms 	1 box\n\n")
        
        f.write("# setting mass, mag. moments, and interactions for bcc iron\n\n")
        
        f.write("mass		1 55.845\n\n")
        
        
        f.write("# set 		group all spin/random 31 2.2\n")
        f.write("set 		group all spin 2.2 0.0 0.0 1.0\n")

        
        f.write("pair_style 	hybrid/overlay eam/alloy spin/exchange 3.5\n")
        f.write("pair_coeff 	* * eam/alloy Fe_Mishin2006.eam.alloy Fe\n")
        f.write("pair_coeff 	* * spin/exchange exchange 3.4 0.02726 0.2171 1.841\n\n")
        
        f.write("neighbor 	0.1 bin\n")
        f.write("neigh_modify 	every 10 check yes delay 20\n\n")
        
        f.write("fix 		1 all precession/spin zeeman 0.0 0.0 0.0 1.0\n")
        f.write("fix_modify 	1 energy yes\n")
        f.write("fix 		2 all langevin/spin {}.0 0.01 21\n\n".format(int(temp)))
        
        f.write("fix 		3 all nve/spin lattice moving\n")
        f.write("timestep	0.0001\n\n")
        
        f.write("# compute and output options\n\n")
        
        f.write("compute 	out_mag    all spin\n")
        f.write("compute 	out_pe     all pe\n")
        f.write("compute 	out_ke     all ke\n")
        f.write("compute 	out_temp   all temp\n\n")
        
        f.write("variable 	magz      equal c_out_mag[3]\n")
        f.write("variable 	magnorm   equal c_out_mag[4]\n")
        f.write("variable 	emag      equal c_out_mag[5]\n")
        f.write("variable 	tmag      equal c_out_mag[6]\n\n")
        
        f.write("thermo_style    custom step time v_magnorm v_tmag temp v_emag ke pe press etotal\n")
        f.write("thermo          5000\n\n")
        
        f.write("compute 	outsp all property/atom spx spy spz sp fmx fmy fmz\n")
        f.write("dump 		1 all custom 100 dump_iron.lammpstrj type x y z c_outsp[1] c_outsp[2] c_outsp[3]\n\n")
        
        f.write("run 		100000\n")
        
        f.write("# run 2\n\n")

        f.write("unfix 3\n")
        f.write("fix 3 all nve/spin lattice moving\n")
        f.write("velocity 	all create {} 4928459 rot yes dist gaussian\n\n".format(int(temp)))
        f.write("run     100000")
        f.close()
