""" From repo example
    https://github.com/MaximeRivest/dspy-lm-auth/blob/main/README.md
"""

import dspy
import dspy_lm_auth


dspy_lm_auth.install()

student_lm = dspy.LM(
    "ollama_chat/qwen3.5:0.8b",
    api_base="http://127.0.0.1:11434",
    api_key="ollama",
    model_type="chat",
    think=False,
    temperature=0,
    max_tokens=200,
)

reflection_lm = dspy.LM("codex/gpt-5.4")

dspy.configure(lm=student_lm, adapter=dspy.JSONAdapter())


class TranslateFrenchToEnglish(dspy.Signature):
    """Translate the French input into short, natural English."""

    french: str = dspy.InputField(desc="French sentence")
    english: str = dspy.OutputField(desc="Natural English translation")


translator = dspy.Predict(TranslateFrenchToEnglish)

pairs = [
    ("bonjour", "hello"),
    ("merci beaucoup", "thank you very much"),
    ("où est la gare ?", "where is the train station?"),
    ("je suis fatigué", "I am tired"),
    ("il fait très chaud aujourd'hui", "it is very hot today"),
    ("je ne comprends pas", "I do not understand"),
    ("pouvez-vous m'aider ?", "can you help me?"),
    ("j'aime apprendre le français", "I like learning French"),
    ("nous arrivons demain matin", "we are arriving tomorrow morning"),
    ("combien ça coûte ?", "how much does it cost?"),
]

examples = [
    dspy.Example(french=fr, english=en).with_inputs("french")
    for fr, en in pairs
]

trainset = examples[:8]
valset = examples[8:]

print("Before optimization:")
print(translator(french="où est la gare ?").english)
print(translator(french="je ne comprends pas").english)
print()


def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    guess = pred.english.strip()
    target = gold.english.strip()

    exact = guess.lower() == target.lower()
    score = 1.0 if exact else 0.0

    if exact:
        feedback = (
            "Exact match. Keep translations short, natural, and direct. "
            "Do not add explanations."
        )
    else:
        feedback = (
            f"Expected {target!r} but got {guess!r}. "
            "Prefer direct, idiomatic English. Preserve tense, pronouns, and politeness. "
            "Do not explain the translation or add extra words."
        )

    return dspy.Prediction(score=score, feedback=feedback)


gepa = dspy.GEPA(
    metric=metric,
    reflection_lm=reflection_lm,
    auto="light",
)

optimized = gepa.compile(translator, trainset=trainset, valset=valset)

print("Optimized instruction:\n")
print(optimized.signature.instructions)
print()

print("After optimization:")
print(optimized(french="où est la gare ?").english)
print(optimized(french="je ne comprends pas").english)
print(optimized(french="combien ça coûte ?").english)

