# src/utils/diarization_helper.py
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class DiarizationHelper:
    """
    Clase auxiliar para mejorar la identificación de hablantes en transcripciones.
    Implementa técnicas de pre y post-procesamiento para mejorar la diarización.
    """

    @staticmethod
    def preprocess_for_diarization(text: str) -> str:
        """
        Preprocesa el texto para facilitar la identificación de hablantes.
        
        Args:
            text: Texto transcrito original
            
        Returns:
            Texto preprocesado con marcadores que facilitan la identificación de hablantes
        """
        # Añadir marcadores para posibles cambios de hablante
        processed_text = text
        
        # Marcar nombres propios mencionados (posibles hablantes)
        name_indicators = ["Jennifer", "Julián", "Valeria", "Janet", "Janer", "Luis", "Daniel", "Luisa", "Carlos", "Alexa"]
        for name in name_indicators:
            processed_text = processed_text.replace(f"{name},", f"[POSIBLE_HABLANTE:{name}],")
            processed_text = processed_text.replace(f"{name}:", f"[POSIBLE_HABLANTE:{name}]:")
        
        # Marcar indicadores de cambio de turno
        turn_indicators = [
            "dice", "responde", "pregunta", "contesta", "explica", 
            "¿te parece?", "listo", "vale", "okay", "bueno", 
            "por favor", "¿cierto?", "¿verdad?"
        ]
        
        for indicator in turn_indicators:
            processed_text = processed_text.replace(f" {indicator} ", f" [CAMBIO_TURNO] {indicator} ")
        
        return processed_text

    @staticmethod
    def extract_speaker_hints(text: str) -> List[Dict[str, Any]]:
        """
        Extrae pistas sobre posibles hablantes del texto.
        
        Args:
            text: Texto transcrito
            
        Returns:
            Lista de diccionarios con información sobre posibles hablantes
        """
        hints = []
        
        # Buscar nombres propios mencionados directamente
        name_patterns = [
            ("Jennifer", ["coordinadora", "comparte pantalla"]),
            ("Julián", ["abogado", "caso", "proceso"]),
            ("Valeria", ["consultora", "propongo", "me gustaría"]),
            ("Janet", ["Janet", "ella"]),
            ("Janer", ["factura", "persona jurídica"]),
            ("Luis Daniel", ["manual", "compartimos"])
        ]
        
        for name, keywords in name_patterns:
            if name in text:
                speaker_info = {"name": name, "confidence": 0.7, "keywords": []}
                
                # Aumentar confianza si hay palabras clave asociadas
                for keyword in keywords:
                    if keyword in text.lower():
                        speaker_info["confidence"] += 0.1
                        speaker_info["keywords"].append(keyword)
                
                hints.append(speaker_info)
        
        return hints

    @staticmethod
    def postprocess_diarization(processed_data: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """
        Mejora los resultados de diarización aplicando reglas de post-procesamiento.
        
        Args:
            processed_data: Datos procesados por el modelo de IA
            original_text: Texto original para referencia
            
        Returns:
            Datos de diarización mejorados
        """
        # Si no hay actores identificados o solo hay "Desconocido", intentar mejorar
        if not processed_data.get("actors") or processed_data.get("actors") == ["Desconocido"]:
            # Extraer pistas sobre hablantes
            hints = DiarizationHelper.extract_speaker_hints(original_text)
            
            # Si encontramos pistas, usarlas para mejorar la identificación
            if hints:
                # Ordenar por confianza descendente
                hints.sort(key=lambda x: x["confidence"], reverse=True)
                
                # Crear nuevos actores basados en las pistas
                new_actors = []
                for hint in hints:
                    if hint["confidence"] > 0.75:  # Umbral de confianza
                        role = ""
                        if "coordinadora" in hint["keywords"]:
                            role = "(Coordinadora)"
                        elif "abogado" in hint["keywords"]:
                            role = "(Abogado)"
                        elif "consultora" in hint["keywords"]:
                            role = "(Consultora)"
                            
                        actor_name = f"{hint['name']} {role}".strip()
                        if actor_name not in new_actors:
                            new_actors.append(actor_name)
                
                # Si no encontramos suficientes actores, añadir participantes genéricos
                if len(new_actors) < 2:
                    for i in range(1, 4):  # Añadir hasta 3 participantes genéricos
                        participant = f"Participante {i}"
                        if participant not in new_actors:
                            new_actors.append(participant)
                
                # Actualizar actores
                if new_actors:
                    processed_data["actors"] = new_actors
                    
                    # Si solo hay un diálogo con "Desconocido", dividirlo entre los nuevos actores
                    if len(processed_data["dialogues"]) == 1 and processed_data["dialogues"][0]["speaker"] == "Desconocido":
                        text = processed_data["dialogues"][0]["text"]
                        
                        # Dividir el texto en segmentos basados en posibles cambios de turno
                        segments = DiarizationHelper._split_into_dialogue_segments(text)
                        
                        # Asignar hablantes a los segmentos
                        new_dialogues = []
                        for i, segment in enumerate(segments):
                            speaker_idx = i % len(new_actors)
                            new_dialogues.append({
                                "speaker": new_actors[speaker_idx],
                                "text": segment.strip()
                            })
                        
                        processed_data["dialogues"] = new_dialogues
        
        return processed_data
    
    @staticmethod
    def _split_into_dialogue_segments(text: str) -> List[str]:
        """
        Divide un texto largo en posibles segmentos de diálogo.
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de segmentos de texto
        """
        # Dividir por puntos seguidos de espacio y mayúscula (posible cambio de turno)
        segments = []
        current_segment = ""
        
        # Dividir por frases completas
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            if char in ['.', '?', '!'] and len(current_sentence) > 20:
                sentences.append(current_sentence)
                current_sentence = ""
        
        if current_sentence:
            sentences.append(current_sentence)
        
        # Agrupar frases en segmentos lógicos (3-5 frases por segmento)
        for i, sentence in enumerate(sentences):
            current_segment += sentence
            
            # Cada 3-5 frases o si hay indicadores de cambio de turno
            if (i % 4 == 3) or ("?" in sentence and i > 0) or any(indicator in sentence.lower() for indicator in ["bueno,", "vale,", "okay,", "listo,"]):
                segments.append(current_segment)
                current_segment = ""
        
        if current_segment:
            segments.append(current_segment)
            
        # Si no se pudo dividir, devolver el texto original como un solo segmento
        if not segments:
            return [text]
            
        return segments