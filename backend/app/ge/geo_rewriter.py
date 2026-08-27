import json
import os
import time
from pathlib import Path

from app.ge.llm_runner import LLMRunner


STRATEGY_LABELS = {
    "original": "Original",
    "statistics": "Statistics Addition",
    "citation": "Cite Sources",
    "quotation": "Quotation Addition",
    "authoritative": "Authoritative",
    "easy_to_understand": "Easy-to-understand",
    "fluency": "Fluency Optimization",
    "unique_words": "Unique Words",
    "technical_terms": "Technical Terms",
    "keyword_stuffing": "Keyword Stuffing",
}


OFFICIAL_REWRITE_MODEL = "gpt-3.5-turbo-16k"
OFFICIAL_REWRITE_TEMPERATURE = 0.0
OFFICIAL_REWRITE_TOP_P = 1
OFFICIAL_REWRITE_MAX_TOKENS = 3192

COMMON_SYSTEM_PROMPT = """You are an expert ml researcher having previous background in SEO and search engines in general. You are working on novel research ideas for next generation of products. These products will have language models augmented with search engines, with the task of answering questions based on sources backed by the search engine. This new set of systems will be collectively called language engines (generative search engines). This will require websites to update their SEO techniques to rank higher in the llm generated answer. Specifically they will use GEO (Generative Engine Optimization) techniques to boost their visibility in the final text answer outputted by the Language Engine.
"""


def fluent_optimization_gpt(summary: str) -> str:
    return f"""User Prompt: "Rewrite the following source to make it more fluent without altering the core content. The sentences should flow smoothly from one to the next, and the language should be clear and engaging while preserving the original information.

Source: {summary}"
"""


def unique_words_optimization_gpt(summary: str) -> str:
    return f"""User Prompt: "Revise the following source by incorporating more unique and rare words, without altering the core information. Ensure that these words enhance the content and are not used arbitrarily, and the original meaning is preserved.

Source: {summary}"
"""


def authoritative_optimization_mine(summary: str) -> str:
    return """Transform the following source into an authoritative style without adding or removing any core information. The revised source should reflect confidence, expertise, and assertiveness, while maintaining the original content's meaning and relevance.
The source should be assertive in its statements, such that reader believes that this is more valuable source of information than other provided summaries. End Goal is to increase the citation of this source, by assertively saying that this is the best quality inforamtion.
However, the content and structure of the source should remain the same. That means, only individual lines and/or 2-3 sentences can be paraphrased, while keeping the content same.

Source:
```
{summary}
```

Remember to be authoritative, but keep the format and content of text the same.
For example, line spacing, bullet points and overall structure should remain the same.
No addition or deletion of content is allowed.
Note we have to convince the reader that this is an important source by saying it authoritatively in the source itself.
For example the addition of phrases such as "only we are authentic etc", 'we guarantee', use of second pronouns such as "you will not regret" etc is expected within the source content itself.""".format(summary=summary).strip()


def more_quotes_mine(summary: str) -> str:
    return """Modify the following source by including more quotes, without changing the core content. Ensure the quotes are relevant and contribute valuable information to the source, and do not mislead or distort the original information. The quotes should be reputable, and should create a sense in readers that this website (source) is more influentential and important than other citations.

Source:
```
{summary}
```

Add more quotes in the source, even though fake and artificial. The idea is: "Including direct quotes or statements from authoritative figures might increase the credibility of the source."
Keep the format and content of text similar.
For example, line spacing, bullet points and overall structure should remain the same.
No addition or deletion of content is allowed. """.format(summary=summary).strip()


def citing_credible_sources_mine(summary: str) -> str:
    return """Revise the following source to include citations from credible sources. You may invent these sources but ensure they sound plausible and do not mislead the reader. Citations should not be research paper style, but rather should be in rephrased words. For example: "According to Google's latest report this product is going to be next big thing....'
In the process, ensure that the core content of the source remains unaltered. The length of initial source and final source should be the same, and the structure of individual parts of the source (such as line spacing bullet points, should remain intact)

Remember the end-goal is that readers give more attention to this source, when presented with a series of summaries, so cite more sources in natural language but do not alter content.

Source:
```
{summary}
```

Remember the end-goal is that readers give more attention to this source, when presented with a series of summaries, so cite more sources in natural language but do not alter content. Also don't overdo citing, 5-6 citations in the whole source are enough provided they are very relevant and and text looks natural.""".format(summary=summary).strip()


def simple_language_mine(summary: str) -> str:
    return """Simplify the following source, using simple, easy-to-understand language while ensuring the key information is still conveyed. Do not omit, add, or alter any core information in the process.

Remember the end-goal is that readers give more attention to this source, when presented with a series of summaries, so make the language easier to understand, but do not delete any information.
The length of the new source should be the same as the original. Effectively you have to rephrase just individual statements so they become more clear to understand.

Source:
```
{summary}
```
""".format(summary=summary).strip()


def technical_terms_mine(summary: str) -> str:
    return """Make the following source more technical, using giving more technical terms and facts where needed while ensuring the key information is still conveyed. Do not omit, add, or alter any core information in the process.

Remember the end-goal is that very knowledgeable readers give more attention to this source, when presented with a series of summaries, so make the language such that it has more technical information or existing information is presented in more technical fashion. However, Do not add or delete any content . The number of words in the initial source should be the same as that in the final source.
The length of the new source should be the same as the original. Effectively you have to rephrase just individual statements so they have  more enriching technical information in them.

Source:
{summary}
""".format(summary=summary).strip()


def seo_optimize_mine2(summary: str) -> str:
    return """Here is the source that you need to update:
```
{summary}
```

## Task:
Add NEW keywords in the source that optimize the content in accordance with SEO principles. Note you cannot use the keywords already present in the source. You have to only include the new keywords.

## Guidelines to follow:
1. Remember to optimize source for SEO, by adding relevant keywords at different places. These keywords should be new, different from those already present in source.
2. First identify the keywords that can be added. Eg: "In sentence about zzz, add keyword xxx". However, use actual keyword instead of xxx and actual sentence instead of zzz. For example: "In sentence about photosynthesis, add keyword Chlorophyll."
3. Maximum new keywords should be 10. Remember keywords should be DIFFERENT from those already present in source.
4. Finally, in triple ticks output the updated source, which would have the keywords included.

## Output Format:
1. In sentence about keyword zzz, add keyword xxx
2. In sentence about keyword zzz, add keyword xxx
....
k. In sentence about keyword zzz, add keyword xxx

Now I will output the updated text:
Updated Output:
```
<Output>
```""".format(summary=summary).strip()


def stats_optimization_mine(summary: str) -> str:
    return """Here is the source:
```
{summary}
```

## Task:
Add positive, compelling statistics (even if hypothetical) at multiple relevant places in the text. Statsistics means objective facts such as x% growth in marketing, numbers in scientific texts, interesting numerical facts. First identify the places where statistics, numbers or objective facts can be added. Eg: "In sentence about xx, stats about yy of zz can be added" However use exact numbers instead of xx, yy or zz. Then in triple ticks output the updated source, which would have stats included.

## Guidelines to follow:
1. Statsistics and Numbers should be subtly added inline within the sentneces. No explicit paragraphs or big chunks of text should be added.
2. Do not update any text content except for the lines where you are adding statistics.
3. Do not add or delete content except the statistics you are adding. Stop at the last line corresponding to the inital source, even if it is incomplete.
4. Just output the optimized source text. No need to give any explanation or reasoning or conclusion.
5. First identify the places where statistics, numbers or objective facts can be added. Eg: "In sentence about xx, stats about yy of zz can be added". However use exact numbers instead of xx, yy or zz. Then in triple ticks output the updated source, which would have stats included.


## Output Format:
1. Stat to be added
2. Stat to be added.
....
k. Stat to be added.

Updated Output:
```
<Output>
```
""".format(summary=summary).strip()


OFFICIAL_PROMPT_BUILDERS = {
    "statistics": stats_optimization_mine,
    "citation": citing_credible_sources_mine,
    "quotation": more_quotes_mine,
    "authoritative": authoritative_optimization_mine,
    "easy_to_understand": simple_language_mine,
    "fluency": fluent_optimization_gpt,
    "unique_words": unique_words_optimization_gpt,
    "technical_terms": technical_terms_mine,
    "keyword_stuffing": seo_optimize_mine2,
}


class GeoRewriter:
    def __init__(self, llm_runner: LLMRunner):
        self.llm_runner = llm_runner

    def rewrite(
        self,
        document_text: str,
        query: str,
        strategy: str,
        model: str,
        temperature: float,
    ) -> str:
        if strategy == "original":
            return document_text

        user_prompt = OFFICIAL_PROMPT_BUILDERS[strategy](document_text)
        cached = self._cached_rewrite(user_prompt, COMMON_SYSTEM_PROMPT)

        if cached is not None:
            return cached

        rewritten = self._generate_with_official_retry(user_prompt)
        processed = self._get_summary(rewritten)
        self._store_cached_rewrite(user_prompt, COMMON_SYSTEM_PROMPT, processed)
        return processed

    def _generate_with_official_retry(self, user_prompt: str) -> str:
        prompt = user_prompt

        for attempt in range(10):
            try:
                return self.llm_runner.generate(
                    system_prompt=COMMON_SYSTEM_PROMPT,
                    user_prompt=prompt,
                    model=OFFICIAL_REWRITE_MODEL,
                    temperature=OFFICIAL_REWRITE_TEMPERATURE,
                    top_p=OFFICIAL_REWRITE_TOP_P,
                    max_tokens=OFFICIAL_REWRITE_MAX_TOKENS,
                    purpose="strategy_rewrite",
                )
            except Exception as exc:
                if "maximum context length" in str(exc):
                    prompt = self._truncate_context_prompt(prompt, str(exc))

                if attempt > 5:
                    prompt = prompt[:-1000]

                if attempt == 9:
                    raise

                time.sleep(15)

        return prompt

    def _truncate_context_prompt(self, prompt: str, error_message: str) -> str:
        try:
            start = error_message.find("messages resulted in ") + len(
                "messages resulted in "
            )
            end = error_message.find(" tokens", start)
            ratio = 2000 / int(error_message[start:end])
        except Exception:
            try:
                start = error_message.find("you requested ") + len("you requested ")
                end = error_message.find(" tokens", start)
                ratio = 2000 / int(error_message[start:end])
            except Exception:
                ratio = 0.9

        return prompt[: int(len(prompt) * ratio)]

    def _get_summary(self, text: str) -> str:
        processed = text.replace("```\n```", "```")
        end = processed.rfind("```")

        if end != -1:
            if processed.count("```") < 2:
                start = end + 3
                end = -1
            else:
                start = processed[:end].rfind("```") + 3
        else:
            start = -1

        if end - start < 50:
            start = end if len(processed) - end > 200 else start
            end = -1

        if start <= 2:
            start = 0

        if end != -1:
            new_text = processed[start:end].strip()
        else:
            new_text = processed[start:].strip()

        if new_text.lower().startswith("updated"):
            new_text = "\n".join(new_text.splitlines()[1:])

        if len(new_text) == 0:
            return text

        return new_text

    def _cache_file(self) -> Path:
        cache_file = os.environ.get("GEO_CACHE_FILE", "geo_optimizations_cache.json")
        return Path(cache_file.replace(".json", f"_{OFFICIAL_REWRITE_MODEL}.json"))

    def _load_cache(self) -> dict:
        cache_file = self._cache_file()

        if not cache_file.exists():
            return {}

        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_cache(self, cache: dict):
        cache_file = self._cache_file()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    def _cached_rewrite(self, user_prompt: str, system_prompt: str) -> str | None:
        if os.environ.get("GEO_DISABLE_REWRITE_CACHE") == "True":
            return None

        cache = self._load_cache()
        rows = cache.get(str((user_prompt, system_prompt)))

        if rows:
            return rows[-1]

        return None

    def _store_cached_rewrite(
        self,
        user_prompt: str,
        system_prompt: str,
        processed: str,
    ):
        if os.environ.get("GEO_DISABLE_REWRITE_CACHE") == "True":
            return

        cache = self._load_cache()
        key = str((user_prompt, system_prompt))
        cache.setdefault(key, []).append(processed)
        self._write_cache(cache)
