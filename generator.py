import pandas as pd
import random
import numpy as np
import streamlit as st
import base64
import io
st.title('BK Shift Generator: Maak automatisch BK week schema\'s!')

st.markdown("""
Maak programma maakt BK week schema\'s om het werk van de secri pupil te verzachten! 
Een aantal regels om errors te vermijden:
* Houd de structuur van de sheets hetzelfde!!
* Hij luistert alleen naar heel, half en 0. Als er een waarde in staat anders dan dat, ziet hij dat als 0
* Een lege cel vult hij automatisch op met de waarde van de cel erboven
* Hij pakt  alle kolommen tot en met de ingevulde laatste persoon variabel, en alle rijen tot en met de rij nummer variabel
* Als 1 iemand maar heeft opgegeven voor een shift, dan krijgt alleen dit persoon de shift
**Github:** https://github.com/rensvendrig/BoardShiftGenerator.
\nGemaakt door Rens Vendrig. Vragen over de app? Mail dan naar rensvendrig121@gmail.com!
""")

def filedownload(all_dfs, sheet):
    # excel = df.to_excel(index=False)
    # b64 = base64.b64encode(excel.encode()).decode()  # strings <-> bytes conversions
    # href = f'<a href="data:file/csv;base64,{b64}" download="BK_Schema_Week_{text}.csv">Download Schema voor Week {text}</a>'
    # towrite = io.BytesIO()

    with pd.ExcelWriter('BK_Schema_Weken.xlsx') as writer:
        for df, week_num in all_dfs:
            df.to_excel(writer, sheet_name=str(week_num))
    with open(writer, 'rb') as f:
        f.seek(0)  # reset pointer
        b64 = base64.b64encode(f.read()).decode()  # some strings
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="BK_Schema_{sheet}.csv">Download Schema voor {sheet}</a>'
    return href

def create_df(excel_name, SHEET, LAST_ROW, LAST_MEMBER, NAMES):
    df = pd.read_excel(excel_name, sheet_name=SHEET)
    df = df.loc[:int(LAST_ROW) - 2, :LAST_MEMBER]
    df.rename(columns={'Unnamed: 0': 'datum', 'Unnamed: 1': 'tijd'}, inplace=True)
    df.ffill(inplace=True)
    df[NAMES] = df[NAMES].replace(regex=r'\bheel\b|\bHeel\b', value=2)
    df[NAMES] = df[NAMES].replace(regex=r'\bhalf\b|\bHalf\b', value=1)
    df[NAMES] = df[NAMES].replace(regex=r'^((?!heel)|(?!half).)*$', value=0)
    # for a, b in df.iterrows():
    #     if pd.isnull(b.datum):
    #         df.iloc[a,'datum'] = df.iloc[a-1,'datum']
    df['totalshifts'] = df.groupby(['datum'])['tijd'].transform('count')

    # def make_half_zero(df):

    # def check_rules(df):

    # df['BeschikbaarheidPercentage'] = df.apply(lambda x: x.count(), axis=1)/len(df.columns)*100

    df = pd.pivot_table(df, index=['datum', 'tijd'])
    df['availablePercentage'] = (df == 0).astype(int).sum(axis=1)
    df['availablePercentage'] = df['availablePercentage'].max() - df['availablePercentage']
    df.reset_index(inplace=True)
    #     df = df.sort_values(by=['availablePercentage'])
    return df


# '''Chooses someone randomly to be shifted in, when all the members have equal amount of shifts already'''
def choose_name(name_list, mydict):
    subset = {key: mydict[key] for key in name_list}
    min_val = min(subset.values())
    names = [k for k, v in subset.items() if v == min_val]
    if len(names) >= 2:
        # TODO:
        # hier implementeren dat als de personen die kunnen een 2 hebben en de vorige shift hebben dan hun een shift weer geven
        return random.sample(names, 2)
    elif len(names) == 1:
        del subset[names[0]]
        if subset == {}:
            return names
        min_val = min(subset.values())
        names2 = [k for k, v in subset.items() if v == min_val]
        names.append(random.choice(names2))
        return names


def assign_shift(df, mydict, names_dict, names_with_not_0, x):
    names = choose_name(names_with_not_0, mydict)
    for name in names:
        df[name][x] = True
        mydict[name] += 1

        for remaining_names in [x for x in names_dict.keys() if x not in names]:
            df[remaining_names][x] = False

        try:
            if df[name][x + 1] == 1 and df['datum'][x] == df['datum'][x + 1]:
                df.iat[x + 1, df.columns.get_loc(name)] = 0

        except (KeyError, IndexError):
            pass

    return df, mydict


def get_names_with_not_0(name_dict):
    return [k for k, v in name_dict.items() if v != 0]


def make_scheme(df, dfWeekendShiftCount):
    dfNormalShiftCount = dict.fromkeys(NAMES, 0)
    for x, y in df.iterrows():
        #         if y['availablePercentage'] == 0:
        #             continue
        #         else:
        names_dict = y[NAMES].to_dict()
        names_with_not_0 = get_names_with_not_0(names_dict)
        # maak hier check voor de members die in ook gelijke dagen al hebben in het dfNormalShiftCount of weekend, dat je dan een randomizer doet
        if y['totalshifts'] == 1:
            df, dfWeekendShiftCount = assign_shift(df, dfWeekendShiftCount, names_dict, names_with_not_0, x)
        else:
            df, dfNormalShiftCount = assign_shift(df, dfNormalShiftCount, names_dict, names_with_not_0, x)

    df.set_index(['datum', 'tijd'], inplace=True)

    df.drop(['totalshifts', 'availablePercentage'], axis=1, inplace=True)

    df.replace({False: None, True: 1}, inplace=True)

    df = df.T

    df['#shifts'] = df.sum(axis=1)

    df.replace({np.NaN: ""}, inplace=True)

    week_num = "Week " + str(df.columns[0][0].week)

    df.columns = rename_columns(df)

    return df.reindex(NAMES), dfNormalShiftCount, dfWeekendShiftCount, week_num


def rename_columns(df):
    new_columns = []
    for timestamp, shift in df.columns:
        if timestamp != '#shifts':
            day_name = str(timestamp.day_name('Dutch').lower())
            day = str(timestamp.day)
            month_name = str(timestamp.month_name('Dutch').lower())
            new_timestamp = day_name + " " + day + " " + month_name
        else:
            new_timestamp = timestamp

        new_columns.append((new_timestamp, shift))

    new = pd.MultiIndex.from_tuples(new_columns, names=['datum', 'tijd'])
    return new


excel_name = st.file_uploader("Upload Beschikbaarheid Schema")

if excel_name is not None:
    col1, col2 = st.columns(2)
    with col1:
        SHEET = st.text_input("Naam sheet", 'September 2021')
        LAST_ROW = st.text_input("Laatste rijnummer", 50)
    with col2:
        LAST_MEMBER = st.text_input("Laatste bestuurlid", 'Rens')
        NAMES = st.text_input('Alle bestuurleden (gescheiden door een komma-spatie \', \')',
                          'Kris, Myrthe, Thomas, Lukas, Noor, Feline, Lotte, Kyra, Bram, Rens').split(', ')

    start_execution = st.button('Genereer BK Schema')

    if start_execution:
        df = create_df(excel_name, SHEET, LAST_ROW, LAST_MEMBER, NAMES)

        dfWeekendShiftCount = dict.fromkeys(NAMES, 0)

        weeks = [g for n, g in df.groupby(pd.Grouper(key='datum', freq='W'))]

        all_dfs = []
        for weekdf in weeks:
            newdf, dfNormalShiftCount, dfWeekendShiftCount, week_num = make_scheme(weekdf, dfWeekendShiftCount)
            all_dfs.append((newdf, week_num))
        st.markdown(filedownload(all_dfs, SHEET),
                    unsafe_allow_html=True)
