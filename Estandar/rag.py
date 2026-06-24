import ollama
import os
import json
import re

EMBEDDING_MODEL = 'hf.co/CompendiumLabs/bge-base-en-v1.5-gguf'
LANGUAGE_MODEL = 'llama3.2:3b'

VECTOR_DB = []
_cargado = False

def cargar_conocimiento():
    global _cargado
    if _cargado:
        return
    carpeta = os.path.join(os.path.dirname(__file__), 'conocimiento_clinico')
    for nombre in os.listdir(carpeta):
        if nombre.endswith('.txt'):
            ruta = os.path.join(carpeta, nombre)
            with open(ruta, 'r', encoding='utf-8') as f:
                lineas = [l.strip() for l in f.readlines() if l.strip()]
            for linea in lineas:
                embedding = ollama.embed(model=EMBEDDING_MODEL, input=linea)['embeddings'][0]
                VECTOR_DB.append((linea, embedding))
    _cargado = True

def cosine_similarity(a, b):
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    return dot_product / (norm_a * norm_b)

def retrieve(query, top_n=3):
    query_embedding = ollama.embed(model=EMBEDDING_MODEL, input=query)['embeddings'][0]
    similarities = [(chunk, cosine_similarity(query_embedding, emb)) for chunk, emb in VECTOR_DB]
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_n]

def generar_comentarios_batch(errores):
    cargar_conocimiento()

    bloques = []
    for i, err in enumerate(errores):
        query = f"{err['medida']} valor {err['valor']}"
        conocimiento = retrieve(query)
        contexto = "\n".join(f"  - {chunk}" for chunk, _ in conocimiento)
        bloques.append(
            f"Medida {i}: {err['medida']}\n"
            f"Valor registrado: {err['valor']}\n"
            f"Contexto relevante:\n{contexto}"
        )
    contexto_total = "\n\n".join(bloques)

    n = len(errores)  # <-- añade esto antes del prompt
    
    system_prompt = f"""Eres un asistente médico clínico.
El sistema ya ha determinado que estos valores están fuera de los rangos normales:

{contexto_total}

Debes generar exactamente {n} comentarios, uno por cada medida (índices del 0 al {n-1}).
Responde ÚNICAMENTE con un objeto JSON con esta estructura:
{{
  "comentarios": [
    {{"indice": 0, "comentario": "explicacion clinica aqui"}},
    ...hasta el indice {n-1}
  ]
}}

Sustituye "explicacion clinica aqui" por el comentario real de cada medida. No copies el ejemplo, genera comentarios reales.
"""


    respuesta = ollama.chat(
        model=LANGUAGE_MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': 'Genera el JSON con los comentarios.'}
        ]
    )

    contenido = respuesta['message']['content'].strip()
    print("=== CONTENIDO CRUDO ===")
    print(repr(contenido))  # <-- añade aquí, ANTES de cualquier procesamiento
    
    contenido = contenido.replace('```json', '').replace('```', '').strip()
    match = re.search(r'\{.*\}', contenido, re.DOTALL)
    if match:
        contenido = match.group(0)
    else:
        print("=== NO SE ENCONTRÓ JSON EN LA RESPUESTA ===")

    try:
        data = json.loads(contenido)
        resultado = {str(item['indice']): item['comentario'] for item in data.get('comentarios', [])}
        print("RESULTADO FINAL:", resultado)
        return resultado
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print("ERROR PARSING:", e)
        print("RAW:", contenido)
        return {}