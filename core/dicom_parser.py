# core/dicom_parser.py
import os
import pydicom
from pydicom import config
import datetime
from core import database as db

# --- CONFIGURAÇÕES GLOBAIS DO PYDICOM ---
config.convert_wrong_length_to_UN = True
config.enforce_valid_values = False

def identificar_medico(nome_dicom_raw):
    """Limpa e tenta encontrar o registro do médico na string DICOM"""
    if not nome_dicom_raw or str(nome_dicom_raw) == "N/A":
        return "N/A"

    try:
        texto_limpo = str(nome_dicom_raw).replace('^', ' ').strip()
        partes = texto_limpo.split()
        for item in partes:   
            if item.isdigit():
                return item 
    except Exception:
        pass 
    return f"{nome_dicom_raw}"
    
def processar_diretorio_dicom(caminho_upload):
    """
    Varre a pasta, lê os arquivos DICOM SR, extrai as métricas e salva no banco.
    Retorna a quantidade de sucessos e erros para a interface.
    """
    arquivos_processados = 0
    erros = 0

    for raiz, pastas, arquivos in os.walk(caminho_upload):
        for arquivo in arquivos:
            caminho_completo = os.path.join(raiz, arquivo)
            try:
                ds = pydicom.dcmread(caminho_completo, stop_before_pixels=True, force=True)

                if ds.get("Modality") == "SR":
                    nome_medico_bruto = ds.get("PerformingPhysicianName", "N/A")
                    medico_id = identificar_medico(nome_medico_bruto)

                    data_dicom = str(ds.get("StudyDate", ""))
                    if len(data_dicom) == 8:
                        data_formatada = f"{data_dicom[0:4]}-{data_dicom[4:6]}-{data_dicom[6:8]}"
                    else:
                        data_formatada = datetime.date.today().strftime("%Y-%m-%d")
                        
                    metrics = {
                        "Dose": 0.0, 
                        "DAP": 0.0, 
                        "TempoFluoro": 0.0, 
                        #"TempoAcq": 0.0
                    }

                    if hasattr(ds, "ContentSequence"):
                        def extrair_simples(seq, dest):
                            for it in seq:
                                if hasattr(it, "ConceptNameCodeSequence"):
                                    c = it.ConceptNameCodeSequence[0].CodeValue
                                    if hasattr(it, "MeasuredValueSequence"):
                                        valor = float(it.MeasuredValueSequence[0].NumericValue)
                                        if c == "113725": dest["Dose"] = valor
                                        elif c == "113722": dest["DAP"] = valor
                                        elif c == "113730": dest["TempoFluoro"] += valor 
                                if hasattr(it, "ContentSequence"): 
                                    extrair_simples(it.ContentSequence, dest)
                        
                        extrair_simples(ds.ContentSequence, metrics)

                    dose = metrics["Dose"] * 1000 
                    dap = metrics["DAP"] * 1e6    
                    tempo_s = metrics["TempoFluoro"] #+ metrics["TempoAcq"]
                    
                    m, s = divmod(tempo_s, 60)
                    h, m = divmod(m, 60)
                    tempo_fmt = "{:02d}:{:02d}:{:02d}".format(int(h), int(m), int(s))
                    
                    paciente_id = str(ds.get("PatientID", "0"))
                    sexo_raw = str(ds.get("PatientSex", "NI")).upper()
                    sexo = sexo_raw if sexo_raw in ["F", "M"] else "NI"
                    exame_nome = str(ds.get("AdmittingDiagnosesDescription", ds.get("StudyDescription", "NI")))
                    fabricante = ds.get("Manufacturer", "Desconhecido")
                    numero_serie = str(ds.get("DeviceSerialNumber", ""))
                    
                    # Usa o banco de dados para inserir
                    sucesso = db.inserir_exame((data_formatada, medico_id, exame_nome, round(dose, 2), tempo_fmt, round(dap, 2), paciente_id, sexo, f"{fabricante}-{numero_serie}"))
                    
                    if sucesso:
                        arquivos_processados += 1
                    else:
                        erros += 1

            except Exception as e:
                print(f"Erro ao ler {arquivo}: {e}")
                erros += 1
                continue
                
    return arquivos_processados, erros