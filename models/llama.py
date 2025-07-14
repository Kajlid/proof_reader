from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch

model_id = "AI-Sweden-Models/Llama-3-8B"

tokenizer = AutoTokenizer.from_pretrained(model_id)


model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="cpu",
    offload_folder="offload",
)

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer
)

result = pipe(
    "När är den senaste informationen du har tillgång till ifrån?",
    max_new_tokens=128
)
print(result[0]['generated_text'])