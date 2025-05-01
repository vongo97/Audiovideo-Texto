import spacy
from typing import Dict, List
import logging
import re

logger = logging.getLogger(__name__)


class TextProcessor:
    def __init__(self):
        """Inicializa el procesador de texto con spaCy"""
        try:
            logger.info("Cargando modelo de spaCy...")
            self.nlp = spacy.load("es_core_news_lg")
            logger.info("Modelo cargado correctamente")
        except OSError:
            logger.info("Descargando modelo de spaCy...")
            spacy.cli.download("es_core_news_lg")
            self.nlp = spacy.load("es_core_news_lg")

    def process_transcript(self, text: str) -> Dict:
        """
        Procesa el texto transcrito para identificar actores y estructurar diálogos
        """
        logger.info("Procesando transcripción...")

        # Procesar el texto con spaCy
        doc = self.nlp(text)

        # Identificar actores (personas)
        actors = self._extract_actors(doc)

        # Estructurar el texto en párrafos y diálogos
        structured_text = self._structure_text(doc)

        # Asignar diálogos a actores
        dialogue_by_actor = self._assign_dialogues(doc, actors)

        return {
            "actors": actors,
            "structured_text": structured_text,
            "dialogue_by_actor": dialogue_by_actor
        }

    def _extract_actors(self, doc) -> List[str]:
        """Extrae nombres de personas del texto"""
        actors = set()
        for ent in doc.ents:
            if ent.label_ == "PER":
                actors.add(ent.text)
        return list(actors)

    def _structure_text(self, doc) -> str:
        """Estructura el texto en párrafos con puntuación correcta"""
        sentences = []
        current_paragraph = []

        for sent in doc.sents:
            # Limpiar y capitalizar la oración
            cleaned_sent = sent.text.strip()
            if cleaned_sent:
                # Capitalizar primera letra
                cleaned_sent = cleaned_sent[0].upper() + cleaned_sent[1:]

                # Asegurar puntuación correcta
                if not cleaned_sent[-1] in {'.', '?', '!'}:
                    cleaned_sent += '.'

                current_paragraph.append(cleaned_sent)

                # Crear nuevo párrafo después de punto final
                if len(current_paragraph) >= 3:
                    sentences.append(' '.join(current_paragraph))
                    current_paragraph = []

        # Añadir último párrafo si existe
        if current_paragraph:
            sentences.append(' '.join(current_paragraph))

        return '\n\n'.join(sentences)

    def _assign_dialogues(self, doc, actors: List[str]) -> Dict[str, List[str]]:
        """Asigna diálogos a actores identificados"""
        dialogues = {actor: [] for actor in actors}
        dialogues["No identificado"] = []  # Para diálogos sin actor claro

        current_actor = None
        current_dialogue = []

        for sent in doc.sents:
            # Buscar actor en la oración
            actor_found = False
            for ent in sent.ents:
                if ent.label_ == "PER" and ent.text in actors:
                    if current_actor and current_dialogue:
                        dialogues[current_actor].append(
                            ' '.join(current_dialogue))
                        current_dialogue = []
                    current_actor = ent.text
                    actor_found = True
                    break

            # Añadir oración al diálogo actual
            cleaned_sent = sent.text.strip()
            if cleaned_sent:
                current_dialogue.append(cleaned_sent)

            # Si no se encontró actor, asignar al "No identificado"
            if not actor_found and not current_actor:
                current_actor = "No identificado"

        # Añadir último diálogo
        if current_actor and current_dialogue:
            dialogues[current_actor].append(' '.join(current_dialogue))

        return dialogues
