import streamlit as st
import mysql.connector
import decimal
import pandas as pd
from google.oauth2 import service_account
import gspread 
from datetime import datetime, time, timedelta
from collections import Counter
from itertools import combinations

def gerar_df_phoenix(vw_name, base_luck):

    data_hoje = datetime.now()

    data_hoje_str = data_hoje.strftime("%Y-%m-%d")

    # Parametros de Login AWS
    config = {
    'user': 'user_automation_jpa',
    'password': 'luck_jpa_2024',
    'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
    'database': base_luck
    }
    # Conexão as Views
    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()

    request_name = f'SELECT * FROM {vw_name} WHERE {vw_name}.`Data Execucao`>={data_hoje_str}'

    # Script MySql para requests
    cursor.execute(
        request_name
    )
    # Coloca o request em uma variavel
    resultado = cursor.fetchall()
    # Busca apenas o cabecalhos do Banco
    cabecalho = [desc[0] for desc in cursor.description]

    # Fecha a conexão
    cursor.close()
    conexao.close()

    # Coloca em um dataframe e muda o tipo de decimal para float
    df = pd.DataFrame(resultado, columns=cabecalho)
    df = df.applymap(lambda x: float(x) if isinstance(x, decimal.Decimal) else x)
    return df

def puxar_sequencias_hoteis(id_gsheet, lista_abas, lista_nomes_df_hoteis):

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(id_gsheet)

    for index in range(len(lista_abas)):

        aba = lista_abas[index]

        df_hotel = lista_nomes_df_hoteis[index]
        
        sheet = spreadsheet.worksheet(aba)

        sheet_data = sheet.get_all_values()

        st.session_state[df_hotel] = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

        st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'] = \
        st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'] = \
        pd.to_numeric(st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'], errors='coerce')

        st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'] = \
        st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'] = \
        pd.to_numeric(st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'], errors='coerce')

        st.session_state[df_hotel]['Bus'] = \
        st.session_state[df_hotel]['Bus'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Micro'] = \
        st.session_state[df_hotel]['Micro'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Van'] = \
        st.session_state[df_hotel]['Van'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Utilitario'] = \
        st.session_state[df_hotel]['Utilitario'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Sequência'] = pd.to_numeric(st.session_state[df_hotel]['Sequência'], errors='coerce')

def gerar_itens_faltantes(df_servicos, df_hoteis):

    lista_hoteis_df_router = df_servicos['Est Origem'].unique().tolist()

    lista_hoteis_sequencia = df_hoteis['Est Origem'].unique().tolist()

    itens_faltantes = set(lista_hoteis_df_router) - set(lista_hoteis_sequencia)

    itens_faltantes = list(itens_faltantes)

    return itens_faltantes, lista_hoteis_df_router

def inserir_hoteis_faltantes(itens_faltantes, df_hoteis, aba_excel, regiao):

    df_itens_faltantes = pd.DataFrame(itens_faltantes, columns=['Est Origem'])

    st.dataframe(df_itens_faltantes, hide_index=True)

    df_itens_faltantes[['Região', 'Sequência', 'Bus', 'Micro', 'Van', 'Hoteis Juntos p/ Apoios', 'Hoteis Juntos p/ Carro Principal']]=''

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)
    
    spreadsheet = client.open_by_key('1Iu3AW8B0e71yii_hvObcRiF3dctKo30lkRyIpVm0XLw')

    sheet = spreadsheet.worksheet(aba_excel)
    sheet_data = sheet.get_all_values()
    last_filled_row = len(sheet_data)
    data = df_itens_faltantes.values.tolist()
    start_row = last_filled_row + 1
    start_cell = f"A{start_row}"
    
    sheet.update(start_cell, data)

    st.error('Os hoteis acima não estão cadastrados na lista de sequência de hoteis.' + 
             f' Eles foram inseridos no final da lista de {regiao}. Por favor, coloque-os na sequência e tente novamente')

def puxar_dados_phoenix():

    st.session_state.df_router = gerar_df_phoenix('vw_router', 'test_phoenix_noronha')

    st.session_state.df_router = st.session_state.df_router[(st.session_state.df_router['Status da Reserva']!='CANCELADO')].reset_index(drop=True)

    st.session_state.df_router['Data Horario Apresentacao Original'] = st.session_state.df_router['Data Horario Apresentacao']

def transformar_timedelta(intervalo):
    
    intervalo = timedelta(hours=intervalo.hour, minutes=intervalo.minute, seconds=intervalo.second)

    return intervalo

def objeto_intervalo(titulo, valor_padrao, chave):

    intervalo_ref = st.time_input(label=titulo, value=valor_padrao, key=chave, step=300)
    
    intervalo_ref = transformar_timedelta(intervalo_ref)

    return intervalo_ref

def objetos_parametros(row, servico_roteiro):

    with row[0]:

        intervalo_hoteis_bairros_iguais = objeto_intervalo('Intervalo Hoteis | Bairros Iguais', time(0, 2), 'intervalo_hoteis_bairros_iguais')

        intervalo_hoteis_bairros_diferentes = objeto_intervalo('Intervalo Hoteis | Bairros Diferentes', time(0, 5), 'intervalo_hoteis_bairros_diferentes')

    with row[1]:

        horario_passeio = st.time_input('Horário Padrão de Último Hotel', time(8,0), 'horario_passeio')

        max_hoteis = st.number_input('Máximo de Hoteis por Carro', step=1, value=20, key='max_hoteis')

        pax_cinco_min = st.number_input('Paxs Extras', step=1, value=18, key='pax_cinco_min', help='Número de paxs para aumentar intervalo entre hoteis em 5 minutos')

    with row[2]:

        intervalo_pu_hotel = objeto_intervalo('Intervalo Hoteis | Primeiro vs Último', time(0, 30), 'intervalo_pu_hotel')

        pax_max = st.number_input('Máximo de Paxs por Carro', step=1, value=27, key='pax_max')

def verificar_cadeirante(observacao):

    palavra = "CADEIRANTE"
    observacao_upper = str(observacao).upper()

    contador_cadeirante = Counter(palavra)

    palavras_observacao = observacao_upper.split()

    for palavra_observacao in palavras_observacao:
        contador_palavra = Counter(palavra_observacao)

        for letra, quantidade in contador_cadeirante.items():
            if contador_palavra[letra] < quantidade:
                break
        else:
            
            return True

    return False

def criar_df_servicos_2(df_servicos, df_hoteis):

    df_servicos['Total ADT | CHD'] = df_servicos['Total ADT'] + df_servicos['Total CHD']

    df_servicos = pd.merge(df_servicos, df_hoteis, on='Est Origem', how='left')

    df_servicos = df_servicos.sort_values(by=['Modo do Servico', 'Sequência'], ascending=[True, False]).reset_index(drop=True)

    df_servicos['Roteiro']=0

    df_servicos['Carros']=0

    return df_servicos

def definir_horario_primeiro_hotel():

    horario_passeio = st.session_state.horario_passeio

    data_base = datetime.combine(st.session_state.data_roteiro, horario_passeio)

    return data_base

def roteirizar_hoteis_mais_pax_max(df_servicos, roteiro, df_hoteis_pax_max):

    # Roteirizando reservas com mais paxs que a capacidade máxima da frota

    df_ref_reservas_pax_max = df_servicos.groupby(['Modo do Servico', 'Reserva', 'Servico', 'Est Origem']).agg({'Total ADT | CHD': 'sum'}).reset_index()

    df_ref_reservas_pax_max = df_ref_reservas_pax_max[df_ref_reservas_pax_max['Total ADT | CHD']>=st.session_state.pax_max].reset_index()

    if len(df_ref_reservas_pax_max)>0:

        carro=0

        for index in range(len(df_ref_reservas_pax_max)):

            pax_ref = df_ref_reservas_pax_max.at[index, 'Total ADT | CHD']

            modo = df_ref_reservas_pax_max.at[index, 'Modo do Servico']

            servico = df_ref_reservas_pax_max.at[index, 'Servico']

            reserva_ref = df_ref_reservas_pax_max.at[index, 'Reserva']

            hotel = df_ref_reservas_pax_max.at[index, 'Est Origem']

            st.warning(f'O hotel {hotel} da reserva {reserva_ref} tem {pax_ref} paxs e, portanto vai ser roteirizado em um ônibus')

            carro+=1

            df_hotel_pax_max = df_servicos[(df_servicos['Reserva']==reserva_ref)].reset_index()

            df_servicos = df_servicos.drop(index=df_hotel_pax_max.at[index, 'index'])

            df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hotel_pax_max.loc[[index]]], ignore_index=True)

            df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Roteiro']=roteiro

            df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Carros']=carro

    df_ref_sem_juncao = df_servicos[(df_servicos['Bus']=='X')].groupby(['Modo do Servico', 'Servico', 'Est Origem']).agg({'Total ADT | CHD': 'sum'}).reset_index()

    df_ref_sem_juncao = df_ref_sem_juncao[df_ref_sem_juncao['Total ADT | CHD']>=st.session_state.pax_max].reset_index()

    if len(df_ref_sem_juncao)>0:

        for index in range(len(df_ref_sem_juncao)):

            carro=0

            pax_ref = df_ref_sem_juncao.at[index, 'Total ADT | CHD']

            loops = int(pax_ref//st.session_state.pax_max)

            modo = df_ref_sem_juncao.at[index, 'Modo do Servico']

            servico = df_ref_sem_juncao.at[index, 'Servico']

            ref_voo = df_ref_sem_juncao.at[index, 'Voo']

            hotel = df_ref_sem_juncao.at[index, 'Est Origem']

            st.warning(f'O hotel {hotel} do voo {ref_voo} tem {pax_ref} paxs e, portanto vai ser roteirizado em um ônibus')

            for loop in range(loops):

                carro+=1

                df_hotel_pax_max = df_servicos[(df_servicos['Modo do Servico']==modo) & (df_servicos['Servico']==servico) & 
                                                (df_servicos['Voo']==ref_voo) & (df_servicos['Est Origem']==hotel)].reset_index()
                
                paxs_total_ref = 0
                
                for index_2, value in df_hotel_pax_max['Total ADT | CHD'].items():

                    if paxs_total_ref+value>st.session_state.pax_max:

                        break

                    else:

                        paxs_total_ref+=value

                        df_servicos = df_servicos.drop(index=df_hotel_pax_max.at[index_2, 'index'])

                        df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hotel_pax_max.loc[[index_2]]], ignore_index=True)

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Roteiro']=roteiro

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Carros']=carro

    for index in range(len(df_hoteis_pax_max)):

        df_hoteis_pax_max.at[index, 'Data Horario Apresentacao'] = definir_horario_primeiro_hotel()

    # Resetando os índices de df_servicos porque houve exclusão de linhas

    df_servicos = df_servicos.reset_index(drop=True)

    # Excluindo coluna 'index' do dataframe df_hoteis_pax_max

    if 'index' in df_hoteis_pax_max.columns.tolist():

        df_hoteis_pax_max = df_hoteis_pax_max.drop(columns=['index'])

    return df_servicos, df_hoteis_pax_max, roteiro

def definir_intervalo_ref(df, value):

    if df.at[value-1, 'Região']==df.at[value, 'Região']:

        return transformar_timedelta(st.session_state.intervalo_hoteis_bairros_iguais)
    
    elif df.at[value-1, 'Região']!=df.at[value, 'Região']:

        return transformar_timedelta(st.session_state.intervalo_hoteis_bairros_diferentes)

def roteirizar_privativos(roteiro, df_servicos, index, carros):

    carros+=1

    df_servicos.at[index, 'Data Horario Apresentacao'] = definir_horario_primeiro_hotel()
    
    df_servicos.at[index, 'Roteiro'] = roteiro
    
    df_servicos.at[index, 'Carros'] = carros

    return roteiro, df_servicos

def preencher_roteiro_carros(df_servicos, roteiro, carros, value):

    df_servicos.at[value, 'Roteiro'] = roteiro

    df_servicos.at[value, 'Carros'] = carros

    return df_servicos

def abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel):

    carros+=1

    df_servicos.at[index, 'Data Horario Apresentacao'] = definir_horario_primeiro_hotel()

    data_horario_primeiro_hotel = df_servicos.at[index, 'Data Horario Apresentacao']

    paxs_total_roteiro = 0

    bairro = ''

    paxs_total_roteiro+=paxs_hotel

    df_servicos.at[index, 'Roteiro'] = roteiro

    df_servicos.at[index, 'Carros'] = carros

    return carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro

def gerar_horarios_apresentacao(df_servicos, roteiro, max_hoteis):

    carros = 0

    paxs_total_roteiro = 0

    contador_hoteis = 0

    for index in range(len(df_servicos)):

        if df_servicos.at[index, 'Modo do Servico']=='PRIVATIVO POR VEICULO' or df_servicos.at[index, 'Modo do Servico']=='PRIVATIVO POR PESSOA' or df_servicos.at[index, 'Modo do Servico']=='CADEIRANTE':

            roteiro, df_servicos = roteirizar_privativos(roteiro, df_servicos, index)

        elif df_servicos.at[index, 'Modo do Servico']=='REGULAR':

            bairro = ''

            if index==0:

                carros+=1

                df_servicos.at[index, 'Data Horario Apresentacao'] = definir_horario_primeiro_hotel()
                
                data_horario_primeiro_hotel = df_servicos.at[index, 'Data Horario Apresentacao']
                
                if not pd.isna(df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']):
                    
                    paxs_hotel = df_servicos[df_servicos['Hoteis Juntos p/ Carro Principal']==df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_servicos[df_servicos['Est Origem']==df_servicos.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, index)

            elif (df_servicos.at[index, 'Est Origem']==df_servicos.at[index-1, 'Est Origem']) | \
                (df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                df_servicos.at[index, 'Data Horario Apresentacao']=df_servicos.at[index-1, 'Data Horario Apresentacao']

                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, index)

            else:

                contador_hoteis+=1

                bairro=df_servicos.at[index, 'Região']

                if not pd.isna(df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']):
                    
                    paxs_hotel = df_servicos[df_servicos['Hoteis Juntos p/ Carro Principal']==df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_servicos[df_servicos['Est Origem']==df_servicos.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                if contador_hoteis>=max_hoteis:

                    carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, index, index, paxs_hotel)
                    
                    contador_hoteis = 1

                else:

                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                        carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, index, index, paxs_hotel)

                        contador_hoteis = 1

                    else:

                        paxs_total_roteiro+=paxs_hotel

                        if bairro!='':

                            intervalo_ref = definir_intervalo_ref(df_servicos, index)
                            
                        if paxs_hotel>=st.session_state.pax_cinco_min:

                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                        data_horario_hotel = df_servicos.at[index-1, 'Data Horario Apresentacao']-\
                            intervalo_ref

                        if  data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                            carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, index, index, paxs_hotel)

                            contador_hoteis = 1

                        else:

                            df_servicos.at[index, 'Data Horario Apresentacao']=data_horario_hotel

                            df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, index)

    return df_servicos, roteiro

def identificar_apoios_em_df(df_servicos, pax_max_utilitario, pax_max_van, pax_max_micro):

    df_servicos['Apoios'] = ''

    for n_roteiro in df_servicos['Roteiro'].unique().tolist():

        df_ref = df_servicos[df_servicos['Roteiro']==n_roteiro].reset_index()

        for veiculo in df_ref['Carros'].unique().tolist():

            df_ref_2 = df_ref[df_ref['Carros']==veiculo].reset_index(drop=True)

            pax_carro = df_ref[df_ref['Carros']==veiculo]['Total ADT | CHD'].sum()

            limitacao_van = df_ref_2['Van'].isnull().any()

            limitacao_micro = df_ref_2['Micro'].isnull().any()

            limitacao_bus = df_ref_2['Bus'].isnull().any()

            if pax_carro>pax_max_utilitario and pax_carro<=pax_max_van and limitacao_van:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Van'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            elif pax_carro>pax_max_van and pax_carro<=pax_max_micro and limitacao_micro:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Micro'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            elif pax_carro>pax_max_micro and limitacao_bus:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Bus'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            if len(df_ref_2)>1:

                for index in range(len(df_ref_2)):

                    indice = df_ref_2.at[index, 'index']

                    regiao_ref = df_ref_2.at[index, 'Região']

                    if regiao_ref == 'CAMURUPIM':

                        df_servicos.at[indice, 'Apoios']='Y'

    return df_servicos

def gerar_roteiros_apoio(df_servicos, pax_max_micro):

    df_roteiros_apoios = df_servicos[(df_servicos['Apoios']=='X') | (df_servicos['Apoios']=='Y')].reset_index()

    df_roteiros_apoios['Carros Apoios']=''

    df_roteiros_carros = df_roteiros_apoios[['Roteiro', 'Carros']].drop_duplicates().reset_index(drop=True)

    for index, value in df_roteiros_carros['Roteiro'].items():

        veiculo = df_roteiros_carros.at[index, 'Carros']

        df_ref = df_servicos[(df_servicos['Roteiro']==value) & (df_servicos['Carros']==veiculo)].reset_index()

        df_ref_apoios = df_ref[(df_ref['Apoios']=='X')].reset_index(drop=True)

        carros = 1

        paxs_total_roteiro = 0

        contador_hoteis = 0

        bairro = ''

        for index in range(len(df_ref_apoios)):

            if index==0:

                df_ref_apoios.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()

                df_ref_apoios.at[index, 'Data Horario Apresentacao']-=timedelta(hours=0, minutes=10, seconds=0)
                
                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                    paxs_hotel = df_ref_apoios[df_ref_apoios['Hoteis Juntos p/ Carro Principal']==df_ref_apoios.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref_apoios[df_ref_apoios['Est Origem']==df_ref_apoios.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_ref_apoios = preencher_roteiro_carros(df_ref_apoios, value, carros, index)

                contador_hoteis+=1

            elif (df_ref_apoios.at[index, 'Est Origem']==df_ref_apoios.at[index-1, 'Est Origem']) | \
                (df_ref_apoios.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref_apoios.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                df_ref_apoios.at[index, 'Data Horario Apresentacao']=df_ref_apoios.at[index-1, 'Data Horario Apresentacao']

                df_ref_apoios = preencher_roteiro_carros(df_ref_apoios, value, carros, index)

            else:

                bairro=df_ref_apoios.at[index, 'Região']

                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                    paxs_hotel = df_ref_apoios[df_ref_apoios['Hoteis Juntos p/ Carro Principal']==df_ref_apoios.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref_apoios[df_ref_apoios['Est Origem']==df_ref_apoios.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                if paxs_total_roteiro+paxs_hotel>pax_max_micro:

                    carros+=1

                    df_ref_apoios.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()

                    paxs_total_roteiro = 0

                    bairro = ''

                    paxs_total_roteiro+=paxs_hotel

                    df_ref_apoios.at[index, 'Roteiro'] = value

                    df_ref_apoios.at[index, 'Carros'] = carros

                else:

                    paxs_total_roteiro+=paxs_hotel

                    if bairro!='':

                        intervalo_ref = definir_intervalo_ref(df_ref_apoios, index)
                        
                    if paxs_hotel>=st.session_state.pax_cinco_min:

                        intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                    data_horario_hotel = df_ref_apoios.at[index-1, 'Data Horario Apresentacao']-intervalo_ref

                    df_ref_apoios.at[index, 'Data Horario Apresentacao']=data_horario_hotel

                    df_ref_apoios = preencher_roteiro_carros(df_ref_apoios, value, carros, index)

        for index, value in df_ref_apoios['index'].items():

            df_roteiros_apoios.loc[df_roteiros_apoios['index']==value, 'Data Horario Apresentacao']=df_ref_apoios.at[index, 'Data Horario Apresentacao']

            df_roteiros_apoios.loc[df_roteiros_apoios['index']==value, 'Carros Apoios']=df_ref_apoios.at[index, 'Carros']

            df_servicos.at[value, 'Data Horario Apresentacao']=df_ref_apoios.at[index, 'Data Horario Apresentacao']

    if 'index' in df_roteiros_apoios.columns.tolist():

        df_roteiros_apoios = df_roteiros_apoios.drop(columns=['index'])

    return df_servicos, df_roteiros_apoios

def gerar_horarios_apresentacao_2(df_servicos):

    for index in range(len(df_servicos)):

        if index==0:

            df_servicos.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
            
            if not pd.isna(df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                paxs_hotel = df_servicos[df_servicos['Hoteis Juntos p/ Carro Principal']==df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                
            else:

                paxs_hotel = df_servicos[df_servicos['Est Origem']==df_servicos.at[index, 'Est Origem']]['Total ADT | CHD'].sum()


        elif (df_servicos.at[index, 'Est Origem']==df_servicos.at[index-1, 'Est Origem']) | \
            (df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

            df_servicos.at[index, 'Data Horario Apresentacao']=df_servicos.at[index-1, 'Data Horario Apresentacao']

        else:

            bairro=df_servicos.at[index, 'Região']

            if not pd.isna(df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                paxs_hotel = df_servicos[df_servicos['Hoteis Juntos p/ Carro Principal']==df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                
            else:

                paxs_hotel = df_servicos[df_servicos['Est Origem']==df_servicos.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

            if bairro!='':

                intervalo_ref = definir_intervalo_ref(df_servicos, index)
                
            if paxs_hotel>=st.session_state.pax_cinco_min:

                intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

            data_horario_hotel = df_servicos.at[index-1, 'Data Horario Apresentacao']-intervalo_ref

            df_servicos.at[index, 'Data Horario Apresentacao']=data_horario_hotel

    return df_servicos

def roteirizar_pos_apoios(df_roteiros_apoios, df_router_filtrado_2):

    if len(df_roteiros_apoios)>0:

        df_roteiros_carros = df_roteiros_apoios[['Roteiro', 'Carros']].drop_duplicates().reset_index(drop=True)

        for index in range(len(df_roteiros_carros)):

            roteiro_ref = df_roteiros_carros.at[index, 'Roteiro']

            carro_ref = df_roteiros_carros.at[index, 'Carros']

            df_ref = df_router_filtrado_2[(df_router_filtrado_2['Roteiro']==roteiro_ref) & (df_router_filtrado_2['Carros']==carro_ref) & (df_router_filtrado_2['Apoios']=='')].reset_index()

            df_ref = gerar_horarios_apresentacao_2(df_ref)

            for index_2, index_principal in df_ref['index'].items():

                df_router_filtrado_2.at[index_principal, 'Data Horario Apresentacao']=df_ref.at[index_2, 'Data Horario Apresentacao']

    return df_router_filtrado_2

def contar_hoteis_df(df_ref):

    df_ref_contagem_hoteis = df_ref.groupby('Est Origem')['Hoteis Juntos p/ Carro Principal'].first().reset_index()

    hoteis_mesmo_voo=0

    for index in range(len(df_ref_contagem_hoteis)):

        if index==0:

            hoteis_mesmo_voo+=1

        elif not ((df_ref_contagem_hoteis.at[index, 'Hoteis Juntos p/ Carro Principal']==
                  df_ref_contagem_hoteis.at[index-1, 'Hoteis Juntos p/ Carro Principal']) and 
                  (~pd.isna(df_ref_contagem_hoteis.at[index, 'Hoteis Juntos p/ Carro Principal']))):

            hoteis_mesmo_voo+=1

    return hoteis_mesmo_voo

def gerar_roteiros_alternativos(df_servicos):

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())

    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        n_hoteis_df_ref = contar_hoteis_df(df_ref)

        divisao_inteira = n_hoteis_df_ref // df_ref['Carros'].max()

        if n_hoteis_df_ref % df_ref['Carros'].max() == 0:

            max_hoteis = divisao_inteira

        else:

            max_hoteis = divisao_inteira + 1

        carros = 1
    
        paxs_total_roteiro = 0

        contador_hoteis = 0

        bairro = ''

        for index in range(len(df_ref)):

            if index==0:

                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
                
                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
                
                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

                contador_hoteis+=1

            elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | \
                    (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                df_ref.at[index, 'Data Horario Apresentacao']=df_ref.at[index-1, 'Data Horario Apresentacao']

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

            else:

                contador_hoteis+=1

                if contador_hoteis>max_hoteis:

                    carros+=1

                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
                    
                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                    paxs_total_roteiro = 0

                    bairro = ''

                    paxs_total_roteiro+=paxs_hotel

                    df_ref.at[index, 'Roteiro'] = item

                    df_ref.at[index, 'Carros'] = carros
                    
                    contador_hoteis = 1
                    
                else:

                    bairro=df_ref.at[index, 'Região']

                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                            ['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                        carros+=1

                        df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()

                        data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                        paxs_total_roteiro = 0

                        bairro = ''

                        paxs_total_roteiro+=paxs_hotel

                        df_ref.at[index, 'Roteiro'] = item

                        df_ref.at[index, 'Carros'] = carros
                        
                        contador_hoteis = 1

                    else:

                        paxs_total_roteiro+=paxs_hotel

                        if bairro!='':

                            intervalo_ref = definir_intervalo_ref(df_ref, index)
                            
                        if paxs_hotel>=st.session_state.pax_cinco_min:

                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                        data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref

                        if data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                            carros+=1

                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()

                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                            paxs_total_roteiro = 0

                            bairro = ''

                            paxs_total_roteiro+=paxs_hotel

                            df_ref.at[index, 'Roteiro'] = item

                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1

                        else:

                            df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel

                            df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

        df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_ref], ignore_index=True)

    return df_roteiros_alternativos

def gerar_roteiros_alternativos_2(df_servicos, max_hoteis_ref, intervalo_pu_hotel):

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())
    
    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        carros = 1
    
        paxs_total_roteiro = 0

        contador_hoteis = 0

        bairro = ''

        for index in range(len(df_ref)):

            if index==0:

                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
                
                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
                
                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

                contador_hoteis+=1

            elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                df_ref.at[index, 'Data Horario Apresentacao']=df_ref.at[index-1, 'Data Horario Apresentacao']

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

            else:

                contador_hoteis+=1

                if contador_hoteis>max_hoteis_ref:

                    carros+=1

                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
                    
                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                    paxs_total_roteiro = 0

                    bairro = ''

                    paxs_total_roteiro+=paxs_hotel

                    df_ref.at[index, 'Roteiro'] = item

                    df_ref.at[index, 'Carros'] = carros
                    
                    contador_hoteis = 1
                    
                else:

                    bairro=df_ref.at[index, 'Região']

                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                        carros+=1

                        df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()

                        data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                        paxs_total_roteiro = 0

                        bairro = ''

                        paxs_total_roteiro+=paxs_hotel

                        df_ref.at[index, 'Roteiro'] = item

                        df_ref.at[index, 'Carros'] = carros
                        
                        contador_hoteis = 1

                    else:

                        paxs_total_roteiro+=paxs_hotel

                        if bairro!='':

                            intervalo_ref = definir_intervalo_ref(df_ref, index)
                            
                        if paxs_hotel>=st.session_state.pax_cinco_min:

                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                        data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref

                        if data_horario_primeiro_hotel - data_horario_hotel>intervalo_pu_hotel:

                            carros+=1

                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()

                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                            paxs_total_roteiro = 0

                            bairro = ''

                            paxs_total_roteiro+=paxs_hotel

                            df_ref.at[index, 'Roteiro'] = item

                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1

                        else:

                            df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel

                            df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

        df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_ref], ignore_index=True)

    return df_roteiros_alternativos

def gerar_roteiros_alternativos_3(df_servicos):

    df_servicos_ref = df_servicos.sort_values(by=['Roteiro', 'Carros', 'Data Horario Apresentacao']).reset_index(drop=True)

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())

    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos_ref[df_servicos_ref['Roteiro']==item].reset_index(drop=True)

        df_regiao_carro = df_ref[['Região', 'Carros']].drop_duplicates().reset_index(drop=True)

        df_regiao_duplicada = df_regiao_carro.groupby('Região')['Carros'].count().reset_index()

        carros_repetidos = df_regiao_duplicada['Carros'].max()

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        if carros_repetidos>1:

            carros = 1
    
            paxs_total_roteiro = 0
    
            contador_hoteis = 0
    
            bairro = ''
    
            for index in range(len(df_ref)):
    
                if index==0:
    
                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
                    
                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
                    
                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
    
                    paxs_total_roteiro+=paxs_hotel
    
                    df_ref = preencher_roteiro_carros(df_ref, item, carros, index)
    
                    contador_hoteis+=1

                elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | \
                        (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):
    
                    df_ref.at[index, 'Data Horario Apresentacao']=df_ref.at[index-1, 'Data Horario Apresentacao']
    
                    df_ref = preencher_roteiro_carros(df_ref, item, carros, index)
    
                else:

                    bairro_anterior=df_ref.at[index-1, 'Região']

                    bairro=df_ref.at[index, 'Região']

                    if bairro_anterior!=bairro:

                        n_hoteis_novo_bairro = len(df_ref[df_ref['Região']==bairro]['Est Origem'].unique().tolist())

                        paxs_novo_bairro = df_ref[df_ref['Região'] == bairro]['Total ADT | CHD'].sum()

                        if n_hoteis_novo_bairro+contador_hoteis<=st.session_state.max_hoteis and paxs_total_roteiro+paxs_novo_bairro<=st.session_state.pax_max:
    
                            contador_hoteis+=1
            
                            if contador_hoteis>st.session_state.max_hoteis:
            
                                carros+=1
            
                                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
                                
                                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
            
                                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
            
                                paxs_total_roteiro = 0
            
                                bairro = ''
            
                                paxs_total_roteiro+=paxs_hotel
            
                                df_ref.at[index, 'Roteiro'] = item
            
                                df_ref.at[index, 'Carros'] = carros
                                
                                contador_hoteis = 1
                                
                            else:

                                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
            
                                # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                                # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis
            
                                if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:
            
                                    carros+=1
            
                                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
            
                                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
            
                                    paxs_total_roteiro = 0
            
                                    bairro = ''
            
                                    paxs_total_roteiro+=paxs_hotel
            
                                    df_ref.at[index, 'Roteiro'] = item
            
                                    df_ref.at[index, 'Carros'] = carros
                                    
                                    contador_hoteis = 1
            
                                # Se não estourar a capacidade máxima
            
                                else:
            
                                    paxs_total_roteiro+=paxs_hotel
            
                                    # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                                    # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação
            
                                    if bairro!='':
            
                                        intervalo_ref = definir_intervalo_ref(df_ref, index)
                                        
                                    if paxs_hotel>=st.session_state.pax_cinco_min:

                                        intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)
            
                                    data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref
            
                                    if data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):
            
                                        carros+=1
            
                                        df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
            
                                        data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
            
                                        paxs_total_roteiro = 0
            
                                        bairro = ''
            
                                        paxs_total_roteiro+=paxs_hotel
            
                                        df_ref.at[index, 'Roteiro'] = item
            
                                        df_ref.at[index, 'Carros'] = carros
                                        
                                        contador_hoteis = 1
            
                                    else:
            
                                        df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel
            
                                        df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

                        else:

                            carros+=1
            
                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
                            
                            if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                                    ['Total ADT | CHD'].sum()
                                
                            else:
        
                                paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
        
                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
        
                            paxs_total_roteiro = 0
        
                            bairro = ''
        
                            paxs_total_roteiro+=paxs_hotel
        
                            df_ref.at[index, 'Roteiro'] = item
        
                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1

                    else:

                        contador_hoteis+=1
            
                        if contador_hoteis>st.session_state.max_hoteis:
        
                            carros+=1
        
                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
                            
                            if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                                    ['Total ADT | CHD'].sum()
                                
                            else:
        
                                paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
        
                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
        
                            paxs_total_roteiro = 0
        
                            bairro = ''
        
                            paxs_total_roteiro+=paxs_hotel
        
                            df_ref.at[index, 'Roteiro'] = item
        
                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1
                            
                        else:
        
                            bairro=df_ref.at[index, 'Região']
        
                            if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                                    ['Total ADT | CHD'].sum()
                                
                            else:
        
                                paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
        
                            # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                            # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis
        
                            if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:
        
                                carros+=1
        
                                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel()
        
                                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
        
                                paxs_total_roteiro = 0
        
                                bairro = ''
        
                                paxs_total_roteiro+=paxs_hotel
        
                                df_ref.at[index, 'Roteiro'] = item
        
                                df_ref.at[index, 'Carros'] = carros
                                
                                contador_hoteis = 1
        
                            # Se não estourar a capacidade máxima
        
                            else:
        
                                paxs_total_roteiro+=paxs_hotel
        
                                # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                                # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação
        
                                if bairro!='':
        
                                    intervalo_ref = definir_intervalo_ref(df_ref, index)
                                    
                                if paxs_hotel>=st.session_state.pax_cinco_min:

                                    intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                                data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref
        
                                df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel
        
                                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)
    
            df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_ref], ignore_index=True)

    return df_roteiros_alternativos

def gerar_roteiros_alternativos_4(df_servicos, max_hoteis):

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())

    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    # Gerando roteiros alternativos

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        carros = 1
    
        paxs_total_roteiro = 0

        contador_hoteis = 0

        bairro = ''

        for index in range(len(df_ref)):

            # Se for o primeiro hotel do voo, define o horário inicial, colhe o horário do hotel e inicia somatório de paxs do roteiro

            if index==0:

                df_ref.at[index, 'Data Horario Apresentacao']=\
                    definir_horario_primeiro_hotel()
                
                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                        ['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

                contador_hoteis+=1

            # Se não for a primeira linha do voo, mas o hotel for igual o hotel anterior, só repete o horário de apresentação

            elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | \
                    (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                df_ref.at[index, 'Data Horario Apresentacao']=df_ref.at[index-1, 'Data Horario Apresentacao']

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

            # Se não for a primeira linha do voo e o hotel não for igual ao anterior

            else:

                # Colhe a quantidade de paxs do hotel anterior, o bairro do hotel atual, a quantidade de paxs do hotel atual 
                # e verifica se estoura a capacidade máxima de um carro

                contador_hoteis+=1

                if contador_hoteis>max_hoteis:

                    carros+=1

                    df_ref.at[index, 'Data Horario Apresentacao']=\
                        definir_horario_primeiro_hotel()
                    
                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                            ['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    paxs_total_roteiro = 0

                    bairro = ''

                    paxs_total_roteiro+=paxs_hotel

                    df_ref.at[index, 'Roteiro'] = item

                    df_ref.at[index, 'Carros'] = carros
                    
                    contador_hoteis = 1
                    
                else:

                    bairro=df_ref.at[index, 'Região']

                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                            ['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                    # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis

                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                        carros+=1

                        df_ref.at[index, 'Data Horario Apresentacao']=\
                            definir_horario_primeiro_hotel()

                        paxs_total_roteiro = 0

                        bairro = ''

                        paxs_total_roteiro+=paxs_hotel

                        df_ref.at[index, 'Roteiro'] = item

                        df_ref.at[index, 'Carros'] = carros
                        
                        contador_hoteis = 1

                    # Se não estourar a capacidade máxima

                    else:

                        paxs_total_roteiro+=paxs_hotel

                        # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                        # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação

                        if bairro!='':

                            intervalo_ref = definir_intervalo_ref(df_ref, index)
                            
                        if paxs_hotel>=st.session_state.pax_cinco_min:

                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                        data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref

                        df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel

                        df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

        df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_ref], ignore_index=True)

    return df_roteiros_alternativos

def identificar_apoios_em_df_4(df_servicos, pax_max_utilitario, pax_max_van, pax_max_micro):

    df_servicos['Apoios'] = ''

    for n_roteiro in df_servicos['Roteiro'].unique().tolist():

        df_ref = df_servicos[df_servicos['Roteiro']==n_roteiro].reset_index()

        for veiculo in df_ref['Carros'].unique().tolist():

            df_ref_2 = df_ref[df_ref['Carros']==veiculo].reset_index(drop=True)

            pax_carro = df_ref[df_ref['Carros']==veiculo]['Total ADT | CHD'].sum()

            limitacao_van = df_ref_2['Van'].isnull().any()

            limitacao_micro = df_ref_2['Micro'].isnull().any()

            limitacao_bus = df_ref_2['Bus'].isnull().any()

            if pax_carro>pax_max_utilitario and pax_carro<=pax_max_van and limitacao_van:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Van'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            elif pax_carro>pax_max_van and pax_carro<=pax_max_micro and limitacao_micro:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Micro'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            elif pax_carro>pax_max_micro and limitacao_bus:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Bus'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            if len(df_ref_2)>1:

                for index in range(len(df_ref_2)):

                    indice = df_ref_2.at[index, 'index']

                    regiao_ref = df_ref_2.at[index, 'Região']

                    if regiao_ref == 'CAMURUPIM':

                        df_servicos.at[indice, 'Apoios']='Y'

    for n_roteiro in df_servicos['Roteiro'].unique().tolist():

        df_ref_4 = df_servicos[(df_servicos['Roteiro']==n_roteiro)].sort_values(by=['Apoios', 'Sequência'], ascending=[False, True]).reset_index()

        df_ref_4_group_hoteis = df_ref_4.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Apoios': 'first'}).reset_index()

        df_ref_4_group_hoteis = df_ref_4_group_hoteis.sort_values(by='Total ADT | CHD').reset_index(drop=True)

        df_ref_4_group_hoteis['Sequência_2'] = range(1, len(df_ref_4_group_hoteis)+1)

        df_ref_4 = pd.merge(df_ref_4, df_ref_4_group_hoteis[['Est Origem', 'Sequência_2']], on = ['Est Origem'], how='left')

        df_ref_4 = df_ref_4.sort_values(by=['Apoios', 'Sequência_2'], ascending=[False, True]).reset_index(drop=True)

        for veiculo in df_ref_4['Carros'].unique().tolist():

            sem_roteiro = 0

            df_ref_5 = df_ref_4[df_ref_4['Carros']==veiculo].reset_index()

            if len(df_ref_5['Est Origem'].unique().tolist())>1:

                max_hoteis = len(df_ref_5['Est Origem'].unique().tolist()) // 2

                df_ref_5_contagem_hoteis_apoios = df_ref_5[df_ref_5['Apoios']!=''].groupby('Est Origem')['Hoteis Juntos p/ Apoios'].first().reset_index()

                hoteis_total_apoio=0

                for index in range(len(df_ref_5_contagem_hoteis_apoios)):

                    if index==0:

                        hoteis_total_apoio+=1

                    elif not ((df_ref_5_contagem_hoteis_apoios.at[index, 'Hoteis Juntos p/ Apoios']==
                            df_ref_5_contagem_hoteis_apoios.at[index-1, 'Hoteis Juntos p/ Apoios']) and 
                            (~pd.isna(df_ref_5_contagem_hoteis_apoios.at[index, 'Hoteis Juntos p/ Apoios']))):

                        hoteis_total_apoio+=1

                if 'X' in df_ref_5['Apoios'].values:

                    paxs_total_apoio = df_ref_5[df_ref_5['Apoios']=='X']['Total ADT | CHD'].sum()

                else:

                    paxs_total_apoio = 0

                for index in range(len(df_ref_5)):

                    hotel = df_ref_5.at[index, 'Est Origem']

                    if not pd.isna(df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']):
                                        
                        paxs_hotel = df_ref_5[df_ref_5['Hoteis Juntos p/ Apoios']==df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']]\
                            ['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref_5[df_ref_5['Est Origem']==df_ref_5.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    if index==0:

                        if df_ref_5.at[index, 'Apoios']=='':

                            hoteis_total_apoio+=1

                            if paxs_total_apoio+paxs_hotel<=pax_max_van:

                                paxs_total_apoio+=paxs_hotel

                                df_servicos.loc[(df_servicos['Est Origem']==hotel) & (df_servicos['Roteiro']==n_roteiro) & 
                                                (df_servicos['Carros']==veiculo), 'Apoios']='X'

                            else:

                                sem_roteiro = 1

                                break

                    elif df_ref_5.at[index, 'Est Origem']==df_ref_5.at[index-1, 'Est Origem']:

                        df_servicos.loc[(df_servicos['Est Origem']==hotel) & (df_servicos['Roteiro']==n_roteiro) & 
                                                (df_servicos['Carros']==veiculo), 'Apoios']='X'

                    else:

                        
                        if df_ref_5.at[index, 'Apoios']=='':

                            if not ((df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']==df_ref_5.at[index-1, 'Hoteis Juntos p/ Apoios']) and 
                                    (~pd.isna(df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']))):

                                verificador_n_hoteis = hoteis_total_apoio+1

                            else:

                                verificador_n_hoteis = hoteis_total_apoio

                            if verificador_n_hoteis<=max_hoteis and paxs_total_apoio+paxs_hotel<=pax_max_van:

                                if not ((df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']==df_ref_5.at[index-1, 'Hoteis Juntos p/ Apoios']) and 
                                        (~pd.isna(df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']))):

                                    hoteis_total_apoio+=1

                                paxs_total_apoio+=paxs_hotel

                                df_servicos.loc[(df_servicos['Est Origem']==hotel) & (df_servicos['Roteiro']==n_roteiro) & 
                                                (df_servicos['Carros']==veiculo), 'Apoios']='X'

                            else:

                                break

                if sem_roteiro==1:

                    break

        if sem_roteiro==1:

            df_servicos = df_servicos[df_servicos['Roteiro']!=n_roteiro].reset_index(drop=True)

    df_servicos.loc[df_servicos['Região']=='CAMURUPIM', 'Apoios']='Y'

    return df_servicos

def gerar_roteiros_alternativos_5(df_servicos, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis):

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())

    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        n_carro_ref = 0

        while len(df_ref)>0:

            df_ref_group_hotel = df_ref.groupby('Est Origem')['Total ADT | CHD'].sum().reset_index()

            if n_carro_ref==0:

                df_ref_group_carro = df_ref.groupby('Carros')['Total ADT | CHD'].sum().reset_index()

                carro_max = df_ref_group_carro['Total ADT | CHD'].max()

                if carro_max > pax_max_micro:

                    target = st.session_state.pax_max

                elif carro_max > pax_max_van:

                    target = pax_max_micro

                elif carro_max > pax_max_utilitario:

                    target = pax_max_van

            else:

                paxs_total_roteiro = df_ref_group_hotel['Total ADT | CHD'].sum()

                if paxs_total_roteiro > pax_max_micro:

                    target = st.session_state.pax_max

                elif paxs_total_roteiro > pax_max_van:

                    target = pax_max_micro

                elif paxs_total_roteiro > pax_max_utilitario:

                    target = pax_max_van

            n_carro_ref+=1

            closest_sum = None
            closest_indices = []

            if len(df_ref_group_hotel)>=max_hoteis:

                lim_combinacoes = max_hoteis

            else:

                lim_combinacoes = len(df_ref_group_hotel)

            for r in range(1, lim_combinacoes + 1):

                for comb in combinations(df_ref_group_hotel.index, r):

                    current_sum = df_ref_group_hotel.loc[list(comb), 'Total ADT | CHD'].sum()
                    
                    # Se for igual ao target, já encontramos a combinação perfeita
                    if current_sum == target:
                        closest_sum = current_sum
                        closest_indices = list(comb)
                        break
                    
                    # Se estiver mais próximo do que a combinação anterior, atualizamos
                    if closest_sum is None or abs(target - current_sum) < abs(target - closest_sum):
                        closest_sum = current_sum
                        closest_indices = list(comb)
                
                # Parar o loop se a combinação exata foi encontrada
                if closest_sum == target:
                    break

            result_df = df_ref_group_hotel.loc[closest_indices]

            lista_hoteis_melhor_comb = result_df['Est Origem'].tolist()

            df_rota_alternativa = df_ref[df_ref['Est Origem'].isin(lista_hoteis_melhor_comb)].sort_values(by='Sequência', ascending=False).reset_index(drop=True)

            df_rota_alternativa['Carros'] = n_carro_ref

            df_rota_alternativa = gerar_horarios_apresentacao_2(df_rota_alternativa)

            df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_rota_alternativa], ignore_index=True)

            df_ref = df_ref[~df_ref['Est Origem'].isin(lista_hoteis_melhor_comb)].reset_index(drop=True)

    return df_roteiros_alternativos

def verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos):

    lista_roteiros = df_router_filtrado_2['Roteiro'].unique().tolist()

    for roteiro_referencia in lista_roteiros:

        df_servicos_principal = df_router_filtrado_2[(df_router_filtrado_2['Roteiro']==roteiro_referencia)][['Id_Servico', 'Data Horario Apresentacao', 'Roteiro', 'Carros']].reset_index(drop=True)

        df_servicos_alternativo = df_roteiros_alternativos[(df_roteiros_alternativos['Roteiro']==roteiro_referencia)][['Id_Servico', 'Data Horario Apresentacao', 'Roteiro', 'Carros']].reset_index(drop=True)

        df_servicos_alternativo['Id_Servico'] = df_servicos_alternativo['Id_Servico'].astype('int64')

        df_servicos_alternativo['Roteiro'] = df_servicos_alternativo['Roteiro'].astype('int64')

        df_servicos_alternativo['Carros'] = df_servicos_alternativo['Carros'].astype('int64')

        df_servicos_principal['Id_Servico'] = df_servicos_principal['Id_Servico'].astype('int64')

        df_servicos_principal['Roteiro'] = df_servicos_principal['Roteiro'].astype('int64')

        df_servicos_principal['Carros'] = df_servicos_principal['Carros'].astype('int64')

        if df_servicos_principal.equals(df_servicos_alternativo):

            df_roteiros_alternativos = df_roteiros_alternativos[(df_roteiros_alternativos['Roteiro']!=roteiro_referencia)].reset_index(drop=True)

    return df_roteiros_alternativos

def plotar_roteiros_simples(df_servicos, row3, coluna):

    for item in df_servicos['Roteiro'].unique().tolist():

        df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        for carro in df_ref_1['Carros'].unique().tolist():

            df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

            modo = df_ref_2.at[0, 'Modo do Servico']

            total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

            paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

            if modo=='REGULAR':
    
                titulo_roteiro = f'{modo.title()} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

            else:

                reserva = df_ref_2.at[0, 'Reserva']

                titulo_roteiro = f'{modo.title()} | {reserva} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

            df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()

            df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
        
            with row3[coluna]:

                container = st.container(border=True, height=500)

                container.subheader(titulo_roteiro)

                container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                if coluna==2:

                    coluna=0

                else:

                    coluna+=1

    return coluna

def plotar_roteiros_gerais_com_apoio(df_servicos, df_apoios, df_alternativos, df_apoios_alternativos, coluna, row3):

    for item in df_servicos['Roteiro'].unique().tolist():

        if not item in df_alternativos['Roteiro'].unique().tolist():

            df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)
    
            for carro in df_ref_1['Carros'].unique().tolist():
    
                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())
    
                if modo=='REGULAR':

                    titulo_roteiro = f'{modo.title()} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'
    
                else:
    
                    reserva = df_ref_2.at[0, 'Reserva']
    
                    titulo_roteiro = f'{modo.title()} | {reserva} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'
    
                lista_apoios = df_ref_2['Apoios'].unique().tolist()
    
                if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'}).sort_values(by='Data Horario Apresentacao')\
                        .reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:
    
                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:
    
                    container = st.container(border=True, height=500)
    
                    container.subheader(titulo_roteiro)
    
                    if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                    else:
    
                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                    if coluna==2:
    
                        coluna=0
    
                    else:
    
                        coluna+=1
    
                df_ref_apoio = df_apoios[(df_apoios['Roteiro']==item) & (df_apoios['Carros']==carro)].reset_index(drop=True)
    
                if len(df_ref_apoio)>0:
    
                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():
    
                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))
    
                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())
    
                        titulo_roteiro = f'Apoio | Veículo Principal {carro} | Veículo Apoio {carro_2} | {total_hoteis} hoteis | {paxs_total} paxs'
    
                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao')\
                            .reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:
    
                            container = st.container(border=True, height=500)
    
                            container.subheader(titulo_roteiro)
    
                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                            if coluna==2:
    
                                coluna=0
    
                            else:
    
                                coluna+=1

        else:

            if item in  df_alternativos['Roteiro'].unique().tolist():
    
                df_ref_1 = df_alternativos[df_alternativos['Roteiro']==item].reset_index(drop=True)
    
                for carro in df_ref_1['Carros'].unique().tolist():
    
                    df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                    modo = df_ref_2.at[0, 'Modo do Servico']

                    total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                    paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                    if modo=='REGULAR':

                        titulo_roteiro = f'{modo.title()} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'
        
                    else:
        
                        reserva = df_ref_2.at[0, 'Reserva']
        
                        titulo_roteiro = f'{modo.title()} | {reserva} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'
    
                    lista_apoios = df_ref_2['Apoios'].unique().tolist()
    
                    if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                        df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'}).sort_values(by='Data Horario Apresentacao')\
                            .reset_index()
                        
                        df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                    else:
    
                        df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()
                        
                    df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                
                    with row3[coluna]:
    
                        container = st.container(border=True, height=500)
    
                        container.subheader(titulo_roteiro)
    
                        if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                            container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                        else:
    
                            container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                        if coluna==2:
    
                            coluna=0
    
                        else:
    
                            coluna+=1
    
                    df_ref_apoio = df_apoios_alternativos[(df_apoios_alternativos['Roteiro']==item) & (df_apoios_alternativos['Carros']==carro)].reset_index(drop=True)
    
                    if len(df_ref_apoio)>0:
    
                        for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():
    
                            df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                            total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))
    
                            paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                            titulo_roteiro = f'Apoio | Veículo Principal {carro} | Veículo Apoio {carro_2} | {total_hoteis} hoteis | {paxs_total} paxs'
    
                            df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao')\
                                .reset_index()
                            
                            df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                            
                            with row3[coluna]:
    
                                container = st.container(border=True, height=500)
    
                                container.subheader(titulo_roteiro)
    
                                container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                                if coluna==2:
    
                                    coluna=0
    
                                else:
    
                                    coluna+=1

    return coluna

def definir_html(df_ref):

    if 'Data Horario Apresentacao' in df_ref.columns:
        
        df_ref = df_ref.sort_values(by='Data Horario Apresentacao').reset_index(drop=True)

        df_ref['Data Horario Apresentacao'] = df_ref['Data Horario Apresentacao'].dt.strftime('%d/%m/%Y %H:%M:%S')

    html=df_ref.to_html(index=False)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                text-align: center;  /* Centraliza o texto */
            }}
            table {{
                margin: 0 auto;  /* Centraliza a tabela */
                border-collapse: collapse;  /* Remove espaço entre as bordas da tabela */
            }}
            th, td {{
                padding: 8px;  /* Adiciona espaço ao redor do texto nas células */
                border: 1px solid black;  /* Adiciona bordas às células */
                text-align: center;
            }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """

    return html

def definir_html_2(df_ref):

    if 'Data Horario Apresentacao' in df_ref.columns:

        df_ref['Data Horario Apresentacao'] = df_ref['Data Horario Apresentacao'].dt.strftime('%d/%m/%Y %H:%M:%S')

    html=df_ref.to_html(index=False)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                text-align: center;  /* Centraliza o texto */
            }}
            table {{
                margin: 0 auto;  /* Centraliza a tabela */
                border-collapse: collapse;  /* Remove espaço entre as bordas da tabela */
            }}
            th, td {{
                padding: 8px;  /* Adiciona espaço ao redor do texto nas células */
                border: 1px solid black;  /* Adiciona bordas às células */
                text-align: center;
            }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """

    return html

def criar_output_html(nome_html):

    with open(nome_html, "w", encoding="utf-8") as file:

            nome_regiao = ' '.join(nome_html.split()[2:])

            nome_regiao = nome_regiao.replace('.html', '')

            file.write(f'<p style="font-size:50px;">{nome_regiao}</p>\n\n')

            file.write(f'<p style="font-size:40px;">Roteiros</p>\n\n')

def inserir_roteiros_html_com_apoio(nome_html, df_pdf, df_pdf_apoios):

    roteiro = 0

    df_ref = df_pdf[['Roteiro', 'Carros']].drop_duplicates().reset_index(drop=True)

    for index in range(len(df_ref)):

        roteiro_ref = df_ref.at[index, 'Roteiro']

        carro_ref = df_ref.at[index, 'Carros']

        df_ref_roteiro = df_pdf[(df_pdf['Roteiro']==roteiro_ref) & (df_pdf['Carros']==carro_ref)].reset_index(drop=True)

        if carro_ref==1:

            roteiro+=1

        for carro in df_ref_roteiro['Carros'].unique().tolist():

            df_ref_carro = df_ref_roteiro[df_ref_roteiro['Carros']==carro][['Roteiro', 'Carros', 'Modo do Servico', 'Servico', 'Est Origem', 'Total ADT | CHD', 'Data Horario Apresentacao']]\
                .reset_index(drop=True)
            
            total_paxs = df_ref_carro['Total ADT | CHD'].sum()
            
            html = definir_html(df_ref_carro)

            with open(nome_html, "a", encoding="utf-8") as file:

                file.write(f'<p style="font-size:30px;">Roteiro {roteiro} | Carro {carro} | {int(total_paxs)} Paxs</p>\n\n')

                file.write(html)

                file.write('\n\n')

            df_ref_apoio = df_pdf_apoios[(df_pdf_apoios['Roteiro']==roteiro_ref) & (df_pdf_apoios['Carros']==carro_ref)].reset_index(drop=True)

            if len(df_ref_apoio)>0:

                for carro_apoio in df_ref_apoio['Carros Apoios'].unique().tolist():

                    df_ref_carro_apoio = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_apoio][['Roteiro', 'Carros Apoios', 'Modo do Servico', 'Servico', 'Est Origem', 'Total ADT | CHD', 
                                                                                                   'Data Horario Apresentacao']].reset_index(drop=True)
                    
                    total_paxs = df_ref_carro_apoio['Total ADT | CHD'].sum()
            
                    html = definir_html(df_ref_carro_apoio)

                    with open(nome_html, "a", encoding="utf-8") as file:

                        file.write(f'<p style="font-size:30px;">Apoio Roteiro Principal {roteiro} | Carro Principal {carro} | Carro Apoio {carro_apoio} | {int(total_paxs)} Paxs</p>\n\n')

                        file.write(html)

                        file.write('\n\n')

def verificar_rotas_alternativas_ou_plotar_roteiros_com_apoio(df_roteiros_alternativos, row_warning, row3, coluna, df_hoteis_pax_max, df_router_filtrado_2, df_roteiros_apoios, 
                                                              df_roteiros_apoios_alternativos, nome_html):

    if len(st.session_state.df_roteiros_alternativos)>0 or len(st.session_state.df_roteiros_alternativos_2)>0 or len(st.session_state.df_roteiros_alternativos_3)>0 or \
        len(st.session_state.df_roteiros_alternativos_4)>0 or len(st.session_state.df_roteiros_alternativos_5)>0:

        with row_warning[0]:

            st.warning('Existem opções alternativas para algumas rotas. Por favor, informe quais rotas alternativas serão usadas.')

    else:

        lista_dfs = [df_hoteis_pax_max, df_router_filtrado_2, df_roteiros_apoios]

        n_carros = 0

        for df in lista_dfs:
            
            if len(df)>0:

                n_carros += len(df[['Roteiro', 'Carros']].drop_duplicates())

        with row_warning[0]:

            st.header(f'A roteirização usou um total de {n_carros} carros')

        if len(df_hoteis_pax_max)>0:

            coluna = plotar_roteiros_simples(df_hoteis_pax_max, row3, coluna)

        coluna = plotar_roteiros_gerais_com_apoio(df_router_filtrado_2, df_roteiros_apoios, df_roteiros_alternativos, df_roteiros_apoios_alternativos, coluna, row3)

        criar_output_html(nome_html)

        df_pdf = pd.concat([df_router_filtrado_2, df_hoteis_pax_max], ignore_index=True)

        st.session_state.df_insercao = df_pdf[['Id_Reserva', 'Id_Servico', 'Data Horario Apresentacao', 'Data Horario Apresentacao Original']].reset_index(drop=True)

        inserir_roteiros_html_com_apoio(nome_html, df_pdf, df_roteiros_apoios)

        with open(nome_html, "r", encoding="utf-8") as file:

            html_content = file.read()

        st.download_button(
            label="Baixar Arquivo HTML",
            data=html_content,
            file_name=nome_html,
            mime="text/html"
        )

def plotar_roteiros_gerais_alternativos_com_apoio(df_servicos, df_apoios, df_alternativos, df_alternativos_2, df_alternativos_3, df_alternativos_4, df_alternativos_5, df_apoios_alternativos, 
                                                  df_apoios_alternativos_2, df_apoios_alternativos_3, df_apoios_alternativos_4, df_apoios_alternativos_5, coluna, row3):

    df_rotas_alternativas = pd.concat([df_alternativos['Roteiro'], df_alternativos_2['Roteiro'], df_alternativos_3['Roteiro'], df_alternativos_4['Roteiro'], df_alternativos_5['Roteiro']], 
                                      ignore_index=True).reset_index()

    lista_todas_rotas_alternativas = sorted(df_rotas_alternativas['Roteiro'].unique().tolist())

    for item in lista_todas_rotas_alternativas:

        df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        for carro in df_ref_1['Carros'].unique().tolist():

            df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

            modo = df_ref_2.at[0, 'Modo do Servico']

            total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

            paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

            if modo=='REGULAR':
    
                titulo_roteiro = f'{modo.title()} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

            else:

                reserva = df_ref_2.at[0, 'Reserva']

                titulo_roteiro = f'{modo.title()} | {reserva} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

            lista_apoios = df_ref_2['Apoios'].unique().tolist()

            if 'X' in lista_apoios or 'Y' in lista_apoios:

                df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                    .sort_values(by='Data Horario Apresentacao').reset_index()
                
                df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

            else:

                df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                    .sort_values(by='Data Horario Apresentacao').reset_index()
                
            df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
        
            with row3[coluna]:

                container = st.container(border=True, height=500)

                container.subheader(titulo_roteiro)

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                else:

                    container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                if coluna==2:

                    coluna=0

                else:

                    coluna+=1

            df_ref_apoio = df_apoios[(df_apoios['Roteiro']==item) & (df_apoios['Carros']==carro)].reset_index(drop=True)

            if len(df_ref_apoio)>0:

                for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                    df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                    total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                    paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                    titulo_roteiro = f'Apoio | Veículo Principal {carro} | Veículo Apoio {carro_2} | {total_hoteis} hoteis | {paxs_total} paxs'

                    df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                    
                    with row3[coluna]:

                        container = st.container(border=True, height=500)

                        container.subheader(titulo_roteiro)

                        container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                        if coluna==2:

                            coluna=0

                        else:

                            coluna+=1

        if item in  df_alternativos['Roteiro'].unique().tolist():

            df_ref_1 = df_alternativos[df_alternativos['Roteiro']==item].reset_index(drop=True)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':
    
                    titulo_roteiro = f'Opção Alternativa 1 | {modo.title()} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 1 | {modo.title()} | {reserva} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                lista_apoios = df_ref_2['Apoios'].unique().tolist()

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.subheader(titulo_roteiro)

                    if 'X' in lista_apoios or 'Y' in lista_apoios:

                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                    else:

                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

                df_ref_apoio = df_apoios_alternativos[(df_apoios_alternativos['Roteiro']==item) & (df_apoios_alternativos['Carros']==carro)].reset_index(drop=True)

                if len(df_ref_apoio)>0:

                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                        titulo_roteiro = f'Apoio | Opção Alternativa 1 | Veículo Principal {carro} | Veículo Apoio {carro_2} | {total_hoteis} hoteis | {paxs_total} paxs'

                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:

                            container = st.container(border=True, height=500)

                            container.subheader(titulo_roteiro)

                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                            if coluna==2:

                                coluna=0

                            else:

                                coluna+=1

        if item in  df_alternativos_2['Roteiro'].unique().tolist():

            df_ref_1 = df_alternativos_2[df_alternativos_2['Roteiro']==item].reset_index(drop=True)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':
    
                    titulo_roteiro = f'Opção Alternativa 2 | {modo.title()} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 2 | {modo.title()} | {reserva} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                lista_apoios = df_ref_2['Apoios'].unique().tolist()

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.subheader(titulo_roteiro)

                    if 'X' in lista_apoios or 'Y' in lista_apoios:

                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                    else:

                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

                df_ref_apoio = df_apoios_alternativos_2[(df_apoios_alternativos_2['Roteiro']==item) & (df_apoios_alternativos_2['Carros']==carro)].reset_index(drop=True)

                if len(df_ref_apoio)>0:

                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                        titulo_roteiro = f'Apoio | Opção Alternativa 2 | Veículo Principal {carro} | Veículo Apoio {carro_2} | {total_hoteis} hoteis | {paxs_total} paxs'

                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:

                            container = st.container(border=True, height=500)

                            container.subheader(titulo_roteiro)

                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                            if coluna==2:

                                coluna=0

                            else:

                                coluna+=1

        if item in  df_alternativos_3['Roteiro'].unique().tolist():

            df_ref_1 = df_alternativos_3[df_alternativos_3['Roteiro']==item].reset_index(drop=True)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':
    
                    titulo_roteiro = f'Opção Alternativa 3 | {modo.title()} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 3 | {modo.title()} | {reserva} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                lista_apoios = df_ref_2['Apoios'].unique().tolist()

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.subheader(titulo_roteiro)

                    if 'X' in lista_apoios or 'Y' in lista_apoios:

                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                    else:

                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

                df_ref_apoio = df_apoios_alternativos_3[(df_apoios_alternativos_3['Roteiro']==item) & (df_apoios_alternativos_3['Carros']==carro)].reset_index(drop=True)

                if len(df_ref_apoio)>0:

                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                        titulo_roteiro = f'Apoio | Opção Alternativa 3 | Veículo Principal {carro} | Veículo Apoio {carro_2} | {total_hoteis} hoteis | {paxs_total} paxs'

                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:

                            container = st.container(border=True, height=500)

                            container.subheader(titulo_roteiro)

                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                            if coluna==2:

                                coluna=0

                            else:

                                coluna+=1

        if item in  df_alternativos_4['Roteiro'].unique().tolist():

            df_ref_1 = df_alternativos_4[df_alternativos_4['Roteiro']==item].reset_index(drop=True)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':
    
                    titulo_roteiro = f'Opção Alternativa 4 | {modo.title()} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 4 | {modo.title()} | {reserva} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                lista_apoios = df_ref_2['Apoios'].unique().tolist()

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.subheader(titulo_roteiro)

                    if 'X' in lista_apoios or 'Y' in lista_apoios:

                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                    else:

                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

                df_ref_apoio = df_apoios_alternativos_4[(df_apoios_alternativos_4['Roteiro']==item) & (df_apoios_alternativos_4['Carros']==carro)].reset_index(drop=True)

                if len(df_ref_apoio)>0:

                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                        titulo_roteiro = f'Apoio | Opção Alternativa 4 | Veículo Principal {carro} | Veículo Apoio {carro_2} | {total_hoteis} hoteis | {paxs_total} paxs'

                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:

                            container = st.container(border=True, height=500)

                            container.subheader(titulo_roteiro)

                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                            if coluna==2:

                                coluna=0

                            else:

                                coluna+=1

        if item in  df_alternativos_5['Roteiro'].unique().tolist():

            df_ref_1 = df_alternativos_5[df_alternativos_5['Roteiro']==item].reset_index(drop=True)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':
    
                    titulo_roteiro = f'Opção Alternativa 5 | {modo.title()} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 5 | {modo.title()} | {reserva} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                lista_apoios = df_ref_2['Apoios'].unique().tolist()

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.subheader(titulo_roteiro)

                    if 'X' in lista_apoios or 'Y' in lista_apoios:

                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                    else:

                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

                df_ref_apoio = df_apoios_alternativos_5[(df_apoios_alternativos_5['Roteiro']==item) & (df_apoios_alternativos_5['Carros']==carro)].reset_index(drop=True)

                if len(df_ref_apoio)>0:

                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                        titulo_roteiro = f'Apoio | Opção Alternativa 5 | Veículo Principal {carro} | Veículo Apoio {carro_2} | {total_hoteis} hoteis | {paxs_total} paxs'

                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:

                            container = st.container(border=True, height=500)

                            container.subheader(titulo_roteiro)

                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                            if coluna==2:

                                coluna=0

                            else:

                                coluna+=1

    return coluna

def plotar_roteiros_gerais_final_com_apoio(df_servicos, df_apoios, df_alternativos, df_apoios_alternativos, coluna):

    lista_roteiros = df_servicos['Roteiro'].unique().tolist()

    lista_roteiros.extend(df_alternativos['Roteiro'].unique().tolist())

    lista_roteiros = sorted(lista_roteiros)

    for item in lista_roteiros:

        if not item in df_alternativos['Roteiro'].unique().tolist():

            df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)
    
            for carro in df_ref_1['Carros'].unique().tolist():
    
                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':
    
                    titulo_roteiro = f'{modo.title()} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'{modo.title()} | {reserva} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'
    
                lista_apoios = df_ref_2['Apoios'].unique().tolist()
    
                if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:
    
                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:
    
                    container = st.container(border=True, height=500)
    
                    container.subheader(titulo_roteiro)
    
                    if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                    else:
    
                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                    if coluna==2:
    
                        coluna=0
    
                    else:
    
                        coluna+=1
    
                df_ref_apoio = df_apoios[(df_apoios['Roteiro']==item) & (df_apoios['Carros']==carro)].reset_index(drop=True)
    
                if len(df_ref_apoio)>0:
    
                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():
    
                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))
    
                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                        titulo_roteiro = f'Apoio | Veículo Principal {carro} | Veículo Apoio {carro_2} | {total_hoteis} hoteis | {paxs_total} paxs'
    
                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:
    
                            container = st.container(border=True, height=500)
    
                            container.subheader(titulo_roteiro)
    
                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                            if coluna==2:
    
                                coluna=0
    
                            else:
    
                                coluna+=1

        else:

            if item in  df_alternativos['Roteiro'].unique().tolist():
    
                df_ref_1 = df_alternativos[df_alternativos['Roteiro']==item].reset_index(drop=True)
    
                for carro in df_ref_1['Carros'].unique().tolist():
    
                    df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                    modo = df_ref_2.at[0, 'Modo do Servico']

                    total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                    paxs_total = int(df_ref_2['Total ADT | CHD'].sum())
    
                    if modo=='REGULAR':
    
                        titulo_roteiro = f'{modo.title()} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'

                    else:

                        reserva = df_ref_2.at[0, 'Reserva']

                        titulo_roteiro = f'{modo.title()} | {reserva} | {st.session_state.servico_roteiro} | Veículo {carro} | {total_hoteis} hoteis | {paxs_total} paxs'
    
                    lista_apoios = df_ref_2['Apoios'].unique().tolist()
    
                    if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                        df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                    else:
    
                        df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                    df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                
                    with row3[coluna]:
    
                        container = st.container(border=True, height=500)
    
                        container.subheader(titulo_roteiro)
    
                        if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                            container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                        else:
    
                            container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                        if coluna==2:
    
                            coluna=0
    
                        else:
    
                            coluna+=1
    
                    df_ref_apoio = df_apoios_alternativos[(df_apoios_alternativos['Roteiro']==item) & 
                                                                    (df_apoios_alternativos['Carros']==carro)].reset_index(drop=True)
    
                    if len(df_ref_apoio)>0:
    
                        for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():
    
                            df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                            total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))
    
                            paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())
    
                            titulo_roteiro = f'Apoio | Veículo Principal {carro} | Veículo Apoio {carro_2} | {total_hoteis} hoteis | {paxs_total} paxs'
    
                            df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                                .sort_values(by='Data Horario Apresentacao').reset_index()
                            
                            df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                            
                            with row3[coluna]:
    
                                container = st.container(border=True, height=500)
    
                                container.subheader(titulo_roteiro)
    
                                container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                                if coluna==2:
    
                                    coluna=0
    
                                else:
    
                                    coluna+=1

    return coluna

def atualizar_banco_dados(df_exportacao, base_luck):

    st.session_state.df_insercao = st.session_state.df_insercao.drop(st.session_state.df_insercao.index)

    config = {
    'user': 'user_automation',
    'password': 'auto_luck_2024',
    'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
    'database': base_luck
    }
    # Conexão ao banco de dados
    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()
    
    # Coluna para armazenar o status da atualização
    df_exportacao['Status Serviço'] = ''
    df_exportacao['Status Auditoria'] = ''
    
    # Placeholder para exibir o DataFrame e atualizar em tempo real
    placeholder = st.empty()
    for idx, row in df_exportacao.iterrows():
        id_reserva = row['Id_Reserva']
        id_servico = row['Id_Servico']
        currentPresentationHour = str(row['Data Horario Apresentacao Original'])
        newPresentationHour = str(row['Data Horario Apresentacao'])
        
        data = '{"presentation_hour":["' + currentPresentationHour + '","' + newPresentationHour + ' Roteirizador"]}'
        
        #Horário atual em string

        hora_execucao = datetime.now()
    
        hora_execucao_menos_3h = hora_execucao - timedelta(hours=3)

        current_timestamp = int(hora_execucao_menos_3h.timestamp())
        
        try:
            # Atualizar o banco de dados se o ID já existir
            query = "UPDATE reserve_service SET presentation_hour = %s WHERE id = %s"
            cursor.execute(query, (newPresentationHour, id_servico))
            conexao.commit()
            df_exportacao.at[idx, 'Status Serviço'] = 'Atualizado com sucesso'
            
        except Exception as e:
            df_exportacao.at[idx, 'Status Serviço'] = f'Erro: {e}'
        
        try:
            # Adicionar registro de edição na tabela de auditoria
            query = "INSERT INTO changelogs (relatedObjectType, relatedObjectId, parentId, data, createdAt, type, userId, module, hostname) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, null)"
            cursor.execute(query, ('ReserveService', id_servico, id_reserva, data, current_timestamp, 'update', str(st.session_state.df_user['id'].iloc[0]), 'router'))
            conexao.commit()
            df_exportacao.at[idx, 'Status Auditoria'] = 'Atualizado com sucesso'
        except Exception as e:
            df_exportacao.at[idx, 'Status Auditoria'] = f'Erro: {e}'
            
        # Define o estilo para coloração condicional
        styled_df = df_exportacao.style.applymap(
            lambda val: 'background-color: green; color: white' if val == 'Atualizado com sucesso' 
            else ('background-color: red; color: white' if val != '' else ''),
            subset=['Status Serviço', 'Status Auditoria']
        )
        
        # Atualiza o DataFrame na interface em tempo real
        placeholder.dataframe(styled_df, hide_index=True, use_container_width=True)
        # time.sleep(0.5)
    
    cursor.close()
    conexao.close()
    
    return df_exportacao
    
st.set_page_config(layout='wide')

st.title('Roteirizador de Passeios - Noronha')

st.divider()

if not 'df_router' in st.session_state:

    puxar_dados_phoenix()

row1=st.columns(3)

st.divider()

st.header('Parâmetros')

row2=st.columns(3)

st.divider()

with row1[0]:

    atualizar_phoenix = st.button('Atualizar Dados Phoenix')

    if atualizar_phoenix:

        puxar_dados_phoenix()

    container_roteirizar = st.container(border=True)

    data_roteiro = container_roteirizar.date_input('Data do Roteiro', value=None, format='DD/MM/YYYY', key='data_roteiro')

    df_router_data_roteiro = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                        (st.session_state.df_router['Tipo de Servico']=='TOUR') & 
                                                        (st.session_state.df_router['Status do Servico']!='CANCELADO')]\
                                                            .reset_index(drop=True)

    lista_servicos = df_router_data_roteiro['Servico'].unique().tolist()

    servico_roteiro = container_roteirizar.selectbox('Serviço', lista_servicos, index=None, placeholder='Escolha um Serviço', 
                                                     key='servico_roteiro')  

    row_container = container_roteirizar.columns(2)

    with row_container[0]:

        roteirizar = st.button('Roteirizar')

if servico_roteiro:

    objetos_parametros(row2, servico_roteiro)

if roteirizar:

    puxar_sequencias_hoteis('1Iu3AW8B0e71yii_hvObcRiF3dctKo30lkRyIpVm0XLw', ['Hoteis Noronha'], ['df_noronha'])

    st.session_state.dict_regioes_hoteis = {'INFOS': ['df_noronha', 'Noronha', 'Hoteis Noronha', 'Noronha']}

    nome_df_hotel = st.session_state.dict_regioes_hoteis['INFOS'][0]

    nome_html_ref = st.session_state.dict_regioes_hoteis['INFOS'][1]

    nome_aba_excel = st.session_state.dict_regioes_hoteis['INFOS'][2]

    nome_regiao = st.session_state.dict_regioes_hoteis['INFOS'][3]

    df_hoteis_ref = st.session_state[nome_df_hotel].sort_values(by='Sequência', ascending=False).reset_index(drop=True)

    df_hoteis_ref['Sequência'] = range(1, len(df_hoteis_ref)+1)

    df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                    (st.session_state.df_router['Tipo de Servico']=='TOUR') &  
                                                    (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                    (st.session_state.df_router['Servico']==servico_roteiro)].reset_index(drop=True)
    
    df_router_filtrado['Modo do Servico'] = df_router_filtrado.apply(
        lambda row: 'CADEIRANTE' if verificar_cadeirante(row['Observacao']) else row['Modo do Servico'], axis=1)
    
    df_router_filtrado = df_router_filtrado[~df_router_filtrado['Observacao'].str.upper().str.contains('CLD', na=False)]

    if len(df_router_filtrado)==0:
    
        st.error('Depois de filtrar as reservas com CLD na observação não sobraram serviços para roteirizar.')

        st.stop()

    itens_faltantes, lista_hoteis_df_router = gerar_itens_faltantes(df_router_filtrado, df_hoteis_ref)

    pax_max_utilitario = 4

    pax_max_van = 15

    pax_max_micro = 27

    if len(itens_faltantes)==0:

        st.success('Todos os hoteis estão cadastrados na lista de sequência de hoteis')

        df_router_filtrado_2 = criar_df_servicos_2(df_router_filtrado, df_hoteis_ref)

        roteiro=1

        lista_colunas = ['index']

        df_hoteis_pax_max = pd.DataFrame(columns=lista_colunas.extend(df_router_filtrado_2.columns.tolist()))

        df_router_filtrado_2, df_hoteis_pax_max, roteiro = \
            roteirizar_hoteis_mais_pax_max(df_router_filtrado_2, roteiro, df_hoteis_pax_max)
        
        df_router_filtrado_2, roteiro = gerar_horarios_apresentacao(df_router_filtrado_2, roteiro, st.session_state.max_hoteis)

    else:

        inserir_hoteis_faltantes(itens_faltantes, df_hoteis_ref, nome_aba_excel, nome_regiao)

        st.stop()

    df_router_filtrado_2 = identificar_apoios_em_df(df_router_filtrado_2, pax_max_utilitario, pax_max_van, pax_max_micro)

    df_router_filtrado_2, df_roteiros_apoios = gerar_roteiros_apoio(df_router_filtrado_2, pax_max_micro)

    df_router_filtrado_2 = roteirizar_pos_apoios(df_roteiros_apoios, df_router_filtrado_2)

    df_roteiros_alternativos = gerar_roteiros_alternativos(df_router_filtrado_2)

    df_roteiros_alternativos = identificar_apoios_em_df(df_roteiros_alternativos, pax_max_utilitario, pax_max_van, pax_max_micro)

    df_roteiros_alternativos, df_roteiros_apoios_alternativos = gerar_roteiros_apoio(df_roteiros_alternativos, pax_max_micro)

    df_roteiros_alternativos = roteirizar_pos_apoios(df_roteiros_apoios_alternativos, df_roteiros_alternativos)

    max_hoteis_2 = 20

    intervalo_pu_hotel_2 = pd.Timedelta(minutes=45)

    df_roteiros_alternativos_2 = gerar_roteiros_alternativos_2(df_router_filtrado_2, max_hoteis_2, intervalo_pu_hotel_2)

    df_roteiros_alternativos_2 = identificar_apoios_em_df(df_roteiros_alternativos_2, pax_max_utilitario, pax_max_van, pax_max_micro)

    df_roteiros_alternativos_2, df_roteiros_apoios_alternativos_2 = gerar_roteiros_apoio(df_roteiros_alternativos_2, pax_max_micro)

    df_roteiros_alternativos_2 = roteirizar_pos_apoios(df_roteiros_apoios_alternativos_2, df_roteiros_alternativos_2)

    df_roteiros_alternativos_3 = gerar_roteiros_alternativos_3(df_router_filtrado_2)

    df_roteiros_alternativos_3 = identificar_apoios_em_df(df_roteiros_alternativos_3, pax_max_utilitario, pax_max_van, pax_max_micro)

    df_roteiros_alternativos_3, df_roteiros_apoios_alternativos_3 = gerar_roteiros_apoio(df_roteiros_alternativos_3, pax_max_micro)

    df_roteiros_alternativos_3 = roteirizar_pos_apoios(df_roteiros_apoios_alternativos_3, df_roteiros_alternativos_3)

    max_hoteis_4 = st.session_state.max_hoteis*2

    df_roteiros_alternativos_4 = gerar_roteiros_alternativos_4(df_router_filtrado_2, max_hoteis_4)

    df_roteiros_alternativos_4 = identificar_apoios_em_df_4(df_roteiros_alternativos_4, pax_max_utilitario, pax_max_van, pax_max_micro)

    df_roteiros_alternativos_4, df_roteiros_apoios_alternativos_4 = gerar_roteiros_apoio(df_roteiros_alternativos_4, pax_max_micro)

    df_roteiros_alternativos_4 = roteirizar_pos_apoios(df_roteiros_apoios_alternativos_4, df_roteiros_alternativos_4)

    df_roteiros_alternativos_5 = gerar_roteiros_alternativos_5(df_router_filtrado_2, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis_2)

    df_roteiros_alternativos_5 = identificar_apoios_em_df(df_roteiros_alternativos_5, pax_max_utilitario, pax_max_van, pax_max_micro)

    df_roteiros_alternativos_5, df_roteiros_apoios_alternativos_5 = gerar_roteiros_apoio(df_roteiros_alternativos_5, pax_max_micro)

    df_roteiros_alternativos_5 = roteirizar_pos_apoios(df_roteiros_apoios_alternativos_5, df_roteiros_alternativos_5)

    df_roteiros_alternativos = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos)

    df_roteiros_alternativos_2 = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos_2)

    df_roteiros_alternativos_2 = verificar_rotas_identicas(df_roteiros_alternativos, df_roteiros_alternativos_2)

    df_roteiros_alternativos_3 = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos_3)

    df_roteiros_alternativos_3 = verificar_rotas_identicas(df_roteiros_alternativos_2, df_roteiros_alternativos_3)

    df_roteiros_alternativos_3 = verificar_rotas_identicas(df_roteiros_alternativos, df_roteiros_alternativos_3)

    df_roteiros_alternativos_4 = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos_4)

    df_roteiros_alternativos_4 = verificar_rotas_identicas(df_roteiros_alternativos_3, df_roteiros_alternativos_4)

    df_roteiros_alternativos_4 = verificar_rotas_identicas(df_roteiros_alternativos_2, df_roteiros_alternativos_4)

    df_roteiros_alternativos_4 = verificar_rotas_identicas(df_roteiros_alternativos, df_roteiros_alternativos_4)

    df_roteiros_alternativos_5 = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos_5)

    df_roteiros_alternativos_5 = verificar_rotas_identicas(df_roteiros_alternativos_4, df_roteiros_alternativos_5)

    df_roteiros_alternativos_5 = verificar_rotas_identicas(df_roteiros_alternativos_3, df_roteiros_alternativos_5)

    df_roteiros_alternativos_5 = verificar_rotas_identicas(df_roteiros_alternativos_2, df_roteiros_alternativos_5)

    df_roteiros_alternativos_5 = verificar_rotas_identicas(df_roteiros_alternativos, df_roteiros_alternativos_5)

    # Plotando roteiros de cada carro

    st.divider()

    row_warning = st.columns(1)

    row3 = st.columns(3)

    coluna = 0

    hora_execucao = datetime.now().strftime("%Hh%Mm")

    st.session_state.nome_html = f"{str(data_roteiro.strftime('%d-%m-%Y'))} {hora_execucao} {servico_roteiro}.html"

    st.session_state.df_hoteis_pax_max = df_hoteis_pax_max

    st.session_state.df_router_filtrado_2 = df_router_filtrado_2

    st.session_state.df_roteiros_alternativos = df_roteiros_alternativos

    st.session_state.df_roteiros_alternativos_2 = df_roteiros_alternativos_2

    st.session_state.df_roteiros_alternativos_3 = df_roteiros_alternativos_3

    st.session_state.df_roteiros_alternativos_4 = df_roteiros_alternativos_4

    st.session_state.df_roteiros_alternativos_5 = df_roteiros_alternativos_5

    st.session_state.df_roteiros_apoios = df_roteiros_apoios

    st.session_state.df_roteiros_apoios_alternativos = df_roteiros_apoios_alternativos

    st.session_state.df_roteiros_apoios_alternativos_2 = df_roteiros_apoios_alternativos_2

    st.session_state.df_roteiros_apoios_alternativos_3 = df_roteiros_apoios_alternativos_3

    st.session_state.df_roteiros_apoios_alternativos_4 = df_roteiros_apoios_alternativos_4

    st.session_state.df_roteiros_apoios_alternativos_5 = df_roteiros_apoios_alternativos_5

    verificar_rotas_alternativas_ou_plotar_roteiros_com_apoio(df_roteiros_alternativos, row_warning, row3, coluna, df_hoteis_pax_max, df_router_filtrado_2, df_roteiros_apoios, 
                                                    df_roteiros_apoios_alternativos, st.session_state.nome_html)

if 'nome_html' in st.session_state and (len(st.session_state.df_roteiros_alternativos)>0 or len(st.session_state.df_roteiros_alternativos_2)>0 or len(st.session_state.df_roteiros_alternativos_3)>0 or \
        len(st.session_state.df_roteiros_alternativos_4)>0 or len(st.session_state.df_roteiros_alternativos_5)>0):

    st.divider()

    row_rotas_alternativas = st.columns(1)

    row3 = st.columns(3)

    coluna = 0

    lista_rotas_alternativas = st.session_state.df_roteiros_alternativos['Roteiro'].unique().tolist()

    lista_rotas_alternativas_2 = st.session_state.df_roteiros_alternativos_2['Roteiro'].unique().tolist()

    lista_rotas_alternativas_3 = st.session_state.df_roteiros_alternativos_3['Roteiro'].unique().tolist()

    lista_rotas_alternativas_4 = st.session_state.df_roteiros_alternativos_4['Roteiro'].unique().tolist()

    lista_rotas_alternativas_5 = st.session_state.df_roteiros_alternativos_5['Roteiro'].unique().tolist()

    if len(st.session_state.df_router_filtrado_2)>0:

        with row_rotas_alternativas[0]:

            st.markdown('*Rotas Alternativas 1 são rotas que buscam equilibrar a quantidade de hoteis em cada carro.*')

            rotas_alternativas = st.multiselect('Selecione as Rotas Alternativas 1 que serão usadas', lista_rotas_alternativas)

            st.markdown('*Rotas Alternativas 2 são rotas que tentam colocar apenas um carro para o roteiro, desde que o número de hoteis da rota não passe de 10 e o intervalo entre o primeiro e último hotel seja menor que 1 hora.*')

            rotas_alternativas_2 = st.multiselect('Selecione as Rotas Alternativas 2 que serão usadas', lista_rotas_alternativas_2)

            st.markdown('*Rotas Alternativas 3 são rotas que evitam que dois carros de um roteiro estejam buscando um mesmo bairro/micro região.*')

            rotas_alternativas_3 = st.multiselect('Selecione as Rotas Alternativas 3 que serão usadas', lista_rotas_alternativas_3)

            st.markdown('*Rotas Alternativas 4 são rotas que tentam colocar menos carros, compensando com mais apoios.*')

            rotas_alternativas_4 = st.multiselect('Selecione as Rotas Alternativas 4 que serão usadas', lista_rotas_alternativas_4)

            st.markdown('*Rotas Alternativas 5 são rotas que tentam colocar menos carros, lotando os carros ao máximo e importando-se apenas com a quantidade máxima de 10 hoteis.*')

            rotas_alternativas_5 = st.multiselect('Selecione as Rotas Alternativas 5 que serão usadas', lista_rotas_alternativas_5)
        
            gerar_roteiro_final = st.button('Gerar Roteiro Final')

        if not gerar_roteiro_final:

            coluna = plotar_roteiros_gerais_alternativos_com_apoio(st.session_state.df_router_filtrado_2, st.session_state.df_roteiros_apoios, 
                                                        st.session_state.df_roteiros_alternativos, 
                                                        st.session_state.df_roteiros_alternativos_2, 
                                                        st.session_state.df_roteiros_alternativos_3, 
                                                        st.session_state.df_roteiros_alternativos_4, 
                                                        st.session_state.df_roteiros_alternativos_5,
                                                        st.session_state.df_roteiros_apoios_alternativos, 
                                                        st.session_state.df_roteiros_apoios_alternativos_2, 
                                                        st.session_state.df_roteiros_apoios_alternativos_3, 
                                                        st.session_state.df_roteiros_apoios_alternativos_4, 
                                                        st.session_state.df_roteiros_apoios_alternativos_5, coluna, row3)
            
        else:

            if (set(rotas_alternativas) & set(rotas_alternativas_2)) or \
            (set(rotas_alternativas) & set(rotas_alternativas_3)) or \
            (set(rotas_alternativas) & set(rotas_alternativas_4)) or \
            (set(rotas_alternativas) & set(rotas_alternativas_5)) or \
            (set(rotas_alternativas_2) & set(rotas_alternativas_3)) or \
            (set(rotas_alternativas_2) & set(rotas_alternativas_4)) or \
            (set(rotas_alternativas_2) & set(rotas_alternativas_5)) or \
            (set(rotas_alternativas_3) & set(rotas_alternativas_4)) or \
            (set(rotas_alternativas_3) & set(rotas_alternativas_5)) or \
            (set(rotas_alternativas_4) & set(rotas_alternativas_5)):

                st.error('Só pode selecionar uma opção alternativa p/ cada roteiro')

            else:

                if 'df_servico_voos_horarios' in st.session_state:
                    
                    st.session_state['df_servico_voos_horarios'] = pd.DataFrame(columns=['Servico', 'Voo', 'Horario Voo'])

                df_hoteis_pax_max = st.session_state.df_hoteis_pax_max

                df_router_filtrado_2 = st.session_state.df_router_filtrado_2

                df_roteiros_apoios = st.session_state.df_roteiros_apoios

                df_roteiros_apoios_alternativos = pd.DataFrame(columns=st.session_state.df_roteiros_apoios_alternativos.columns.tolist())

                if len(rotas_alternativas)>0:

                    df_roteiros_alternativos = st.session_state.df_roteiros_alternativos\
                        [st.session_state.df_roteiros_alternativos['Roteiro'].isin(rotas_alternativas)].reset_index(drop=True)
                    
                    df_roteiros_apoios_alternativos = st.session_state.df_roteiros_apoios_alternativos\
                        [st.session_state.df_roteiros_apoios_alternativos['Roteiro'].isin(rotas_alternativas)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_apoios = df_roteiros_apoios[~df_roteiros_apoios['Roteiro'].isin(rotas_alternativas)]\
                        .reset_index(drop=True)
                    
                else:

                    df_roteiros_alternativos = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos.columns.tolist())

                if len(rotas_alternativas_2)>0:

                    df_roteiros_alternativos_2 = st.session_state.df_roteiros_alternativos_2\
                        [st.session_state.df_roteiros_alternativos_2['Roteiro'].isin(rotas_alternativas_2)].reset_index(drop=True)
                    
                    df_roteiros_apoios_alternativos_2 = st.session_state.df_roteiros_apoios_alternativos_2\
                        [st.session_state.df_roteiros_apoios_alternativos_2['Roteiro'].isin(rotas_alternativas_2)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas_2)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_apoios = df_roteiros_apoios[~df_roteiros_apoios['Roteiro'].isin(rotas_alternativas_2)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_roteiros_alternativos_2], ignore_index=True)

                    df_roteiros_apoios_alternativos = pd.concat([df_roteiros_apoios_alternativos, df_roteiros_apoios_alternativos_2], 
                                                                ignore_index=True)
                    
                else:

                    df_roteiros_alternativos_2 = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos_2.columns.tolist())

                if len(rotas_alternativas_3)>0:

                    df_roteiros_alternativos_3 = st.session_state.df_roteiros_alternativos_3\
                        [st.session_state.df_roteiros_alternativos_3['Roteiro'].isin(rotas_alternativas_3)].reset_index(drop=True)
                    
                    df_roteiros_apoios_alternativos_3 = st.session_state.df_roteiros_apoios_alternativos_3\
                        [st.session_state.df_roteiros_apoios_alternativos_3['Roteiro'].isin(rotas_alternativas_3)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas_3)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_apoios = df_roteiros_apoios[~df_roteiros_apoios['Roteiro'].isin(rotas_alternativas_3)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_roteiros_alternativos_3], ignore_index=True)

                    df_roteiros_apoios_alternativos = pd.concat([df_roteiros_apoios_alternativos, df_roteiros_apoios_alternativos_3], 
                                                                ignore_index=True)
                    
                else:

                    df_roteiros_alternativos_3 = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos_3.columns.tolist())

                if len(rotas_alternativas_4)>0:

                    df_roteiros_alternativos_4 = st.session_state.df_roteiros_alternativos_4\
                        [st.session_state.df_roteiros_alternativos_4['Roteiro'].isin(rotas_alternativas_4)].reset_index(drop=True)
                    
                    df_roteiros_apoios_alternativos_4 = st.session_state.df_roteiros_apoios_alternativos_4\
                        [st.session_state.df_roteiros_apoios_alternativos_4['Roteiro'].isin(rotas_alternativas_4)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas_4)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_apoios = df_roteiros_apoios[~df_roteiros_apoios['Roteiro'].isin(rotas_alternativas_4)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_roteiros_alternativos_4], ignore_index=True)

                    df_roteiros_apoios_alternativos = pd.concat([df_roteiros_apoios_alternativos, df_roteiros_apoios_alternativos_4], 
                                                                ignore_index=True)
                    
                else:

                    df_roteiros_alternativos_4 = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos_4.columns.tolist())

                if len(rotas_alternativas_5)>0:

                    df_roteiros_alternativos_5 = st.session_state.df_roteiros_alternativos_5\
                        [st.session_state.df_roteiros_alternativos_5['Roteiro'].isin(rotas_alternativas_5)].reset_index(drop=True)
                    
                    df_roteiros_apoios_alternativos_5 = st.session_state.df_roteiros_apoios_alternativos_5\
                        [st.session_state.df_roteiros_apoios_alternativos_5['Roteiro'].isin(rotas_alternativas_5)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas_5)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_apoios = df_roteiros_apoios[~df_roteiros_apoios['Roteiro'].isin(rotas_alternativas_5)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_roteiros_alternativos_5], ignore_index=True)

                    df_roteiros_apoios_alternativos = pd.concat([df_roteiros_apoios_alternativos, df_roteiros_apoios_alternativos_5], 
                                                                ignore_index=True)
                    
                else:

                    df_roteiros_alternativos_5 = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos_5.columns.tolist())

                lista_dfs = [df_hoteis_pax_max, df_roteiros_apoios, df_roteiros_alternativos]

                n_carros = 0

                for df in lista_dfs:
                    
                    if len(df)>0:

                        n_carros += len(df[['Roteiro', 'Carros']].drop_duplicates())

                with row_rotas_alternativas[0]:

                    st.header(f'A roteirização usou um total de {n_carros} carros')

                if len(df_hoteis_pax_max)>0:

                    coluna = plotar_roteiros_simples(df_hoteis_pax_max, row3, coluna)

                coluna = plotar_roteiros_gerais_final_com_apoio(df_router_filtrado_2, df_roteiros_apoios, df_roteiros_alternativos, 
                                                    df_roteiros_apoios_alternativos, coluna)
                
                html = definir_html(st.session_state.df_juncao_voos)

                criar_output_html(st.session_state.nome_html, html)

                df_pdf = pd.concat([df_router_filtrado_2, df_hoteis_pax_max, df_roteiros_alternativos], ignore_index=True)

                df_pdf_apoios = pd.concat([df_roteiros_apoios, df_roteiros_apoios_alternativos], ignore_index=True)

                st.session_state.df_insercao = df_pdf[['Id_Reserva', 'Id_Servico', 'Data Horario Apresentacao', 'Data Horario Apresentacao Original']].reset_index(drop=True)

                inserir_roteiros_html_com_apoio(st.session_state.nome_html, df_pdf, df_pdf_apoios)

                with open(st.session_state.nome_html, "r", encoding="utf-8") as file:

                    html_content = file.read()

                st.download_button(
                    label="Baixar Arquivo HTML",
                    data=html_content,
                    file_name=st.session_state.nome_html,
                    mime="text/html"
                )

if 'df_insercao' in st.session_state and len(st.session_state.df_insercao)>0:

    lancar_horarios = st.button('Lançar Horários')

    if lancar_horarios and len(st.session_state.df_insercao)>0:

        df_insercao = atualizar_banco_dados(st.session_state.df_insercao, 'test_phoenix_noronha')

        st.rerun()
