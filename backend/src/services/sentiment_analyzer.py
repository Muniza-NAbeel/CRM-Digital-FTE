"""
Sentiment Analyzer Service

Analyzes customer message sentiment using OpenAI or fallback keyword-based analysis.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Analyzes sentiment of customer messages.
    """

    def __init__(self):
        self.positive_keywords = [
            "thank", "great", "excellent", "awesome", "love",
            "happy", "pleased", "satisfied", "wonderful", "good",
        ]
        self.negative_keywords = [
            "angry", "terrible", "awful", "hate", "worst",
            "disappointed", "frustrated", "unhappy", "bad", "horrible",
            "useless", "waste", "refund", "cancel", "complaint",
        ]

    async def analyze(self, message: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a message.
        
        Args:
            message: Customer message text
            
        Returns:
            Dict with sentiment label, score, and confidence
        """
        try:
            # Try OpenAI-based analysis
            return await self._analyze_with_openai(message)
        except Exception as e:
            logger.warning(f"OpenAI sentiment analysis failed, using fallback: {e}")
            return self._analyze_with_keywords(message)

    async def _analyze_with_openai(self, message: str) -> Dict[str, Any]:
        """Analyze sentiment using OpenAI."""
        try:
            from openai import AsyncOpenAI
            import os
            import json
            from pydantic import BaseModel
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            
            client = AsyncOpenAI(api_key=api_key)
            
            # Define response schema
            class SentimentResponse(BaseModel):
                label: str
                score: float
                confidence: float
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a sentiment analysis expert. "
                            "Analyze the sentiment of customer messages. "
                            "Respond with ONLY valid JSON in this exact format: "
                            '{"label": "positive|negative|neutral", "score": -1.0 to 1.0, "confidence": 0.0 to 1.0}'
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Analyze the sentiment of this customer message: '{message}'\n"
                            "Consider:\n"
                            "- Positive indicators: gratitude, satisfaction, praise\n"
                            "- Negative indicators: anger, frustration, disappointment, threats\n"
                            "- Neutral indicators: factual questions, mixed feelings\n"
                            "Return ONLY the JSON response."
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"},
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            
            # Validate response
            label = result.get("label", "neutral").lower()
            if label not in ["positive", "negative", "neutral"]:
                label = "neutral"
            
            score = float(result.get("score", 0.0))
            score = max(-1.0, min(1.0, score))  # Clamp to [-1, 1]
            
            confidence = float(result.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

            logger.debug(f"OpenAI sentiment: label={label}, score={score}, confidence={confidence}")

            return {
                "label": label,
                "score": round(score, 3),
                "confidence": round(confidence, 3),
                "model": "openai",
            }

        except Exception as e:
            logger.error(f"OpenAI sentiment analysis error: {e}")
            raise

    def _analyze_with_keywords(self, message: str) -> Dict[str, Any]:
        """
        Fallback keyword-based sentiment analysis.
        """
        message_lower = message.lower()
        
        positive_count = sum(
            1 for word in self.positive_keywords
            if word in message_lower
        )
        negative_count = sum(
            1 for word in self.negative_keywords
            if word in message_lower
        )
        
        # Calculate score
        total = positive_count + negative_count
        if total == 0:
            score = 0.0
            label = "neutral"
        else:
            score = (positive_count - negative_count) / max(total, 1)
            
            if score > 0.3:
                label = "positive"
            elif score < -0.3:
                label = "negative"
            else:
                label = "neutral"
        
        confidence = min(1.0, total / 5.0)  # More matches = higher confidence
        
        result = {
            "label": label,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "model": "keyword",
            "positive_matches": positive_count,
            "negative_matches": negative_count,
        }
        
        logger.debug(f"Keyword sentiment: {result}")
        return result


# ============================================================================
# Convenience Functions
# ============================================================================

_analyzer: Optional[SentimentAnalyzer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get or create sentiment analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer


async def analyze_sentiment(message: str) -> Dict[str, Any]:
    """
    Analyze sentiment of a message.
    
    Args:
        message: Customer message text
        
    Returns:
        Dict with sentiment analysis results
    """
    analyzer = get_sentiment_analyzer()
    return await analyzer.analyze(message)
