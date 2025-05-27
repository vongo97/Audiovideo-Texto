# src/utils/name_normalizer.py
import logging
from typing import Dict, List, Set, Tuple
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class NameNormalizer:
    """
    Clase para normalizar nombres y consolidar hablantes en transcripciones.
    Resuelve problemas como variaciones de nombres (Janet/Janer) y 
    múltiples referencias al mismo hablante.
    """
    
    # Diccionario de nombres conocidos y sus posibles variantes
    KNOWN_NAME_VARIANTS = {
        "janer": ["janet", "janeth", "jael"],
        "julian": ["julio", "julián"],
        "jennifer": ["jeniffer", "jeny", "jenny"],
        "valeria": ["vale", "valentina"],
        "luis": ["luisa", "lucho"],
    }
    
    @staticmethod
    def normalize_names(actors: List[str], dialogues: List[Dict]) -> Tuple[List[str], List[Dict]]:
        """
        Normaliza los nombres de los actores y consolida hablantes duplicados.
        
        Args:
            actors: Lista de actores identificados
            dialogues: Lista de diálogos con hablantes
            
        Returns:
            Tuple con la lista normalizada de actores y diálogos actualizados
        """
        logger.info(f"Normalizando nombres para {len(actors)} actores")
        
        # 1. Extraer nombres base (sin roles)
        name_mapping = {}
        for actor in actors:
            # Extraer el nombre base (antes del paréntesis si existe)
            base_name = actor.split("(")[0].strip()
            name_mapping[actor] = base_name
        
        # 2. Agrupar nombres similares
        normalized_names = {}
        processed_names = set()
        
        # Primero aplicar el diccionario de variantes conocidas
        for actor in actors:
            base_name = name_mapping[actor]
            lower_name = base_name.lower()
            
            # Buscar en variantes conocidas
            for canonical, variants in NameNormalizer.KNOWN_NAME_VARIANTS.items():
                if lower_name == canonical or lower_name in variants:
                    # Conservar el formato original pero con el nombre canónico
                    canonical_name = canonical.capitalize()
                    if "(" in actor:
                        role = actor[actor.find("("):]
                        normalized_name = f"{canonical_name} {role}"
                    else:
                        normalized_name = canonical_name
                    
                    normalized_names[actor] = normalized_name
                    processed_names.add(actor)
                    break
        
        # Para los nombres no procesados, buscar similitudes
        for i, actor1 in enumerate(actors):
            if actor1 in processed_names:
                continue
                
            base_name1 = name_mapping[actor1]
            
            for j, actor2 in enumerate(actors[i+1:], i+1):
                if actor2 in processed_names:
                    continue
                    
                base_name2 = name_mapping[actor2]
                
                # Comparar similitud de nombres
                similarity = SequenceMatcher(None, base_name1.lower(), base_name2.lower()).ratio()
                
                # Si son muy similares (>0.8), considerarlos el mismo
                if similarity > 0.8:
                    # Usar el nombre más largo como canónico
                    if len(base_name1) >= len(base_name2):
                        canonical_base = base_name1
                    else:
                        canonical_base = base_name2
                    
                    # Preservar roles si existen
                    if "(" in actor1:
                        role = actor1[actor1.find("("):]
                        normalized_names[actor1] = f"{canonical_base} {role}"
                    else:
                        normalized_names[actor1] = canonical_base
                        
                    if "(" in actor2:
                        role = actor2[actor2.find("("):]
                        normalized_names[actor2] = f"{canonical_base} {role}"
                    else:
                        normalized_names[actor2] = canonical_base
                        
                    processed_names.add(actor1)
                    processed_names.add(actor2)
        
        # Para los nombres restantes, mantenerlos igual
        for actor in actors:
            if actor not in processed_names:
                normalized_names[actor] = actor
                processed_names.add(actor)
        
        # 3. Actualizar diálogos con nombres normalizados
        updated_dialogues = []
        for dialogue in dialogues:
            speaker = dialogue["speaker"]
            if speaker in normalized_names:
                updated_dialogues.append({
                    "speaker": normalized_names[speaker],
                    "text": dialogue["text"]
                })
            else:
                # Si por alguna razón el hablante no está en el mapeo, mantenerlo igual
                updated_dialogues.append(dialogue)
        
        # 4. Crear lista final de actores normalizados (sin duplicados)
        normalized_actors = list(set(normalized_names.values()))
        
        # 5. Consolidar diálogos consecutivos del mismo hablante
        consolidated_dialogues = []
        current_speaker = None
        current_text = ""
        
        for dialogue in updated_dialogues:
            if dialogue["speaker"] == current_speaker:
                # Mismo hablante, concatenar texto
                current_text += " " + dialogue["text"]
            else:
                # Nuevo hablante, guardar el diálogo anterior si existe
                if current_speaker:
                    consolidated_dialogues.append({
                        "speaker": current_speaker,
                        "text": current_text
                    })
                # Iniciar nuevo diálogo
                current_speaker = dialogue["speaker"]
                current_text = dialogue["text"]
        
        # Añadir el último diálogo
        if current_speaker:
            consolidated_dialogues.append({
                "speaker": current_speaker,
                "text": current_text
            })
        
        logger.info(f"Normalización completada: {len(actors)} actores originales -> {len(normalized_actors)} actores normalizados")
        return normalized_actors, consolidated_dialogues
    
    @staticmethod
    def filter_mentioned_names(actors: List[str]) -> List[str]:
        """
        Filtra los actores que solo son mencionados pero no participan activamente.
        
        Args:
            actors: Lista de actores identificados
            
        Returns:
            Lista filtrada de actores
        """
        # Filtrar actores que contienen "(Mencionado)" o "(Mencionada)"
        return [actor for actor in actors if "(Mencionado)" not in actor and "(Mencionada)" not in actor]