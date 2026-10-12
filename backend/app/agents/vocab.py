from pydantic_ai import Agent, NativeOutput

from app.agents.prompts.vocab_extraction import SYSTEM_PROMPT
from app.schemas.ai_outputs import VocabExtractionAIOutput

vocab_extraction_agent = Agent(
    name="vocab_extractor",
    output_type=NativeOutput(VocabExtractionAIOutput),
    instructions=SYSTEM_PROMPT,
)
