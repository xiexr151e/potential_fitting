"""
A module for the different models for calculating the 
energy of a set of atoms (a fragment)
"""
import numpy

try:
    import psi4
except ImportError:
    pass

try:
    from TensorMol import *
    os.environ["CUDA_VISIBLE_DEVICES"]="CPU" # for TensorMol
except ImportError:
    pass

def sym_to_num(symbol):
    """
    Converts symbols into numbers for TensorMol input
    """
    if symbol == "O":
        return 8
    elif symbol == "H":
        return 1

def calc_energy(frag_str, config):
    """
    Compute the energy using a model requested by the user
    """
    model = config["driver"]["model"]
    if model == "psi4":
        psi4.core.set_output_file("/dev/null", False)
        psi4.set_memory(config["psi4"]["memory"])
        return calc_psi4_energy(frag_str, config)
    
    if model == "TensorMol":
        return TensorMol_convert_str(frag_str, config)

# Water network data is required to be in the same directory under ./networks !!
def GetWaterNetwork(a):
    """
    TensorMol function that loads a pretrained water network
    """
    TreatedAtoms = a.AtomTypes()
    PARAMS["tf_prec"] = "tf.float64"
    PARAMS["NeuronType"] = "sigmoid_with_param"
    PARAMS["sigmoid_alpha"] = 100.0
    PARAMS["HiddenLayers"] = [500, 500, 500]
    PARAMS["EECutoff"] = 15.0
    PARAMS["EECutoffOn"] = 0
    PARAMS["Elu_Width"] = 4.6  # when elu is used EECutoffOn should always equal to 0
    PARAMS["EECutoffOff"] = 15.0
    PARAMS["DSFAlpha"] = 0.18
    PARAMS["AddEcc"] = True
    PARAMS["KeepProb"] = [1.0, 1.0, 1.0, 1.0]
    d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")
    tset = TensorMolData_BP_Direct_EE_WithEle(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
    manager=TFMolManage("water_network",tset,False,"fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw_DSF_elu_Normalize_Dropout",False,False)
    return manager

def En(m, x_, manager):
    """
    Use TensorMol to compute the energy of a fragment
    """
    mtmp = Mol(m.atoms,x_)
    Etotal, Ebp, Ebp_atom, Ecc, Evdw, mol_dipole, atom_charge, gradient = manager.EvalBPDirectEEUpdateSingle(mtmp, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"],PARAMS["EECutoffOff"], True)
    energy = Etotal[0]
    return energy

def calc_psi4_energy(frag_str, config):
    """
    Use PSI4 to compute the energy of a fragment
    """
    psi4_mol = psi4.core.Molecule.create_molecule_from_string(frag_str)
    psi4_mol.update_geometry()

    psi4.set_num_threads(config["psi4"].getint("threads"))
    energy = psi4.energy("{}/{}".format(config["psi4"]["method"],
          config["psi4"]["basis"]), molecule=psi4_mol)
    
    #print(energy)
    return energy

def TensorMol_convert_str(frag_str, config):
    """
    Prepares input data 
    """
    xyz_list = frag_str.split()
    atoms = numpy.array([])
    coords = numpy.array([])
    for i in range(int(len(xyz_list)/4)):
        atoms = numpy.append(atoms, sym_to_num(xyz_list[i*4]))
        coords = numpy.append(coords, xyz_list[i*4+1:(i+1)*4])
    coords = coords.reshape(atoms.size, 3)
    return calc_TensorMol_energy(atoms, coords, config)

def calc_TensorMol_energy(atoms, coords, config):
    """
    Sets up calculation for TensorMol
    """
    molecule = Mol(atoms, coords)
    molset = MSet()
    molset.mols.append(molecule)
    manager = GetWaterNetwork(molset)
    return En(molecule, coords, manager)
