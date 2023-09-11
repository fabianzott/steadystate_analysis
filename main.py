#!/usr/bin/env python

from basico import *
import pandas as pd
import os

def read_excel_file(file_path):
    """
    Read the first column of an excel file and return a list of concentrations and the name from the first cell.

    Parameters:
    file_path (str): The path to the excel file.

    Returns:
    list: List of concentrations.
    str: Name extracted from the first cell.
    """
    df_excel = pd.read_excel(file_path, usecols=[0], header=None)
    excel_column_a_list = df_excel[0].tolist()

    formatted_excel_list = [f"{float(value):.8f}" if isinstance(value, (float, int)) else value for value in
                            excel_column_a_list]
    formatted_excel_list_name = formatted_excel_list[0].strip()
    del formatted_excel_list[0]

    conc_list_from_excel = [float(value) for value in formatted_excel_list]
    return conc_list_from_excel, formatted_excel_list_name


# Reading data from the excel file
conc_list_from_excel, formatted_excel_list_name = read_excel_file("input_conc.xlsx")

# Uploading the COPASI model file .cps!
file_name = './sandwich-equi-Model.cps'  # <-- change model name here, must be in current working directory
model = load_model(file_name)

def cli_initial_conc(species_df, list_of_species_names):
    """
    Prompt the user to select species for defined initial concentrations
    from a list extracted from an excel file.

    Parameters:
    species_df (pd.DataFrame): Dataframe containing species data.
    list_of_species_names (list): List of species names.

    Returns:
    list: List of selected species for initial concentrations.
    """
    list_of_species_init_conc = []

    print("Please select the species for defined initial concentrations regarding to the input.xls excel file")
    print("Method default for non selected species -> see COPASI .cps method file")
    print("Possible species are: ", species_df.index.tolist())
    print("Type 'done' to proceed with the selection.")

    while True:
        species_name_input = input("Please type in a species name: ")

        if species_name_input.lower() == 'done':
            break
        elif species_name_input not in list_of_species_names:
            print("This is not a species that exists in the uploaded model. Try again!")
        else:
            list_of_species_init_conc.append(species_name_input)
            print(f"Current list of selected species: {list_of_species_init_conc}")

    return list_of_species_init_conc


# get species and create the empty dataframe
species_df = get_species()
list_of_species_names = species_df.index.tolist()
list_of_species_names.insert(0, 'name')
steady_state_analysis_df = pd.DataFrame(columns=list_of_species_names)

# generates a list of species that the initial concentration will be changed for
list_of_species_init_conc = cli_initial_conc(species_df, list_of_species_names)


def cli_set_rates():
    """
    Set rates for reactions from user input through the command line interface.
    Users can modify the rate parameters of reactions specified in the COPASI model file.
    """
    parameters_df = get_reaction_parameters()
    list_of_rates = parameters_df.index.tolist()

    print("---------------------------------------------------")
    print(parameters_df)
    print("---------------------------------------------------")
    print("Above you see the reaction parameters that you can change.")
    print(
        "Choose the name of the rate parameter you want to change and then type in the value as floating point number")
    print("---------------------------------------------------")
    print("!!! Type 'done' to proceed with the selection. !!!!")
    print("---------------------------------------------------")
    print("Possible species are: ", parameters_df.index.tolist())

    while True:
        parameter_name = input("Which rate parameter do you want to change?: ")

        if parameter_name.lower() == 'done':
            break

        if parameter_name not in list_of_rates:
            print("This is not a rate parameter name that exists in the uploaded model. Try again!")
            continue

        print(f"Changing rate parameter for: {parameter_name}")

        while True:
            try:
                rate_value = float(input("What is the value you want to change it into?: "))
                break
            except ValueError:
                print("Invalid input. Please enter a valid floating point number.")

        set_reaction_parameters(parameter_name, value=rate_value)

    parameters_df_new = get_reaction_parameters()
    print("Summary of updated reaction rates:")
    print(parameters_df_new)
    print("---------------------------------------------------")


cli_set_rates()


def set_init_conc(list_of_species_init_conc, concentration):
    """
    Set the initial concentration for a list of species.

    Parameters:
    list_of_species_init_conc (list): List of species names (e.g., ['A', 'B']).
    concentration (float or str): The initial concentration to set for the species.

    Raises:
    ValueError: If concentration cannot be converted to a float.

    """
    try:
        concentration = float(concentration)
    except ValueError:
        raise ValueError("The concentration value could not be converted to a float.")

    for spec in list_of_species_init_conc:
        set_species(name=spec, initial_concentration=concentration)


def analyze_steady_states(conc_list_from_excel, list_of_species_init_conc, steady_state_analysis_df):
    """
    Analyze steady states for various initial concentrations.

    Parameters:
    conc_list_from_excel (list): List of concentrations to analyze.
    list_of_species_init_conc (list): List of species names to set initial concentrations for.
    steady_state_analysis_df (pd.DataFrame): Dataframe to store the analysis results.

    Returns:
    pd.DataFrame: Dataframe containing the steady state analysis results.
    """
    for concentration in conc_list_from_excel:
        try:
            # Set the initial concentration for the list of species
            set_init_conc(list_of_species_init_conc, concentration)
        except ValueError as e:
            print(f"Skipping concentration {concentration} due to error: {e}")
            continue

        # Run the steady-state analysis
        run_steadystate()

        # Retrieve the steady-state data for the species
        try:
            steady_state_data = get_species()[['concentration']]
        except KeyError:
            print(f"Could not retrieve concentration data for concentration: {concentration}. Skipping...")
            continue

        # Create a new dataframe with the steady-state data transposed
        new_data = pd.DataFrame(steady_state_data).T

        # Add the current concentration to the new data
        new_data["IP_tot"] = concentration

        # Append the new data to the cumulative dataframe
        steady_state_analysis_df = steady_state_analysis_df.append(new_data)

    return steady_state_analysis_df


def handle_parameters_df():
    """
    Processes the parameters data frame for appending to the steady state analysis data frame.

    Returns:
    pd.DataFrame: The processed parameters data frame.
    """
    parameters_df = get_reaction_parameters()

    # Add a new column named 'rates' with the values of the index
    parameters_df['rates'] = parameters_df.index
    # Reset and drop the old index
    parameters_df.reset_index(drop=True, inplace=True)

    # Move the 'rates' column to position 0
    parameter_cols = parameters_df.columns.tolist()
    parameter_cols.insert(0, parameter_cols.pop(parameter_cols.index('rates')))
    parameters_df = parameters_df[parameter_cols]

    # Drop the 'type' and 'mapped_to' columns
    parameters_df.drop(columns=['type', 'mapped_to', 'reaction'], inplace=True)

    # transpose dataframe and append to steady_state_analysis_df
    parameters_df = parameters_df.T

    # Set row 0 as the new column names
    parameters_df.columns = parameters_df.iloc[0]

    # Drop the first row
    parameters_df = parameters_df.iloc[1:].reset_index(drop=True)

    return parameters_df

# concateate steady_state_analysis_df, parameters_df for csv output
steady_state_analysis_df = pd.concat([steady_state_analysis_df, handle_parameters_df()], axis=1)


steady_state_analysis_df.to_csv('steady_state_analysis.csv', index=False)
print(".csv file generated in :", os.getcwd())
#print(steady_state_analysis_df)
