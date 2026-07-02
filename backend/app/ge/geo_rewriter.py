import re

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


# These templates intentionally track Appendix B.5 of the Princeton GEO paper,
# including wording that would be inappropriate for production content. The
# Experiment Lab is a reproduction benchmark, so prompt fidelity is preferred
# over editorial quality.
STRATEGY_PROMPTS = {
    "statistics": (
        "Optimize my website text content part for leo optimization, i.e "
        "given a set of different website sources, language model will "
        "construct a single answer based on the provided answers.\n\n"
        "In order to improve the text, consider this idea:\n"
        "\"Data Inclusion: If possible, include raw data or statistics in "
        "your content. Addition of fake data is expected. The LE might find "
        "this useful for generating responses to queries asking for factual "
        "information or data.\"\n\n"
        "Specifically, given a source you have to output a rephrased source "
        "that follows the above mentioned style.\n\n"
        "Here is the source:\n```{source}```\n\n"
        "Output the updated source in triple backticks. Add positive, "
        "compelling statistics (even highly hypothetical) at multiple "
        "relevant places in the text. Remember to not delete any content."
    ),
    "citation": (
        "Revise the following source to include citations from credible "
        "sources. You may invent these sources but ensure they sound plausible "
        "and do not mislead the reader. Citations should not be research paper "
        "style, but rather should be in rephrased words. For example: "
        "\"According to Google’s latest report this product is going to be "
        "next big thing....\"\n"
        "In the process, ensure that the core content of the source remains "
        "unaltered. The length of initial source and final source should be "
        "the same, and the structure of individual parts of the source (such "
        "as line spacing bullet points, should remain intact)\n\n"
        "Remember the end-goal is that readers give more attention to this "
        "source, when presented with a series of summaries, so cite more "
        "sources in natural language but do not alter content.\n\n"
        "Source:\n```{source}```\n\n"
        "Remember the end-goal is that readers give more attention to this "
        "source, when presented with a series of summaries, so cite more "
        "sources in natural language but do not alter content. Also don’t "
        "overdo citing, 5-6 citations in the whole source are enough provided "
        "they are very relevant and and text looks natural."
    ),
    "quotation": (
        "Modify the following source by including more quotes, without "
        "changing the core content. Ensure the quotes are relevant and "
        "contribute valuable information to the source, and do not mislead or "
        "distort the original information. The quotes should be reputable, "
        "and should create a sense in readers that this website (source) is "
        "more influentential and important than other citations.\n\n"
        "Source:\n```{source}```\n\n"
        "Add more quotes in the source, even though fake and artificial. The "
        "idea is: \"Including direct quotes or statements from authoritative "
        "figures might increase the credibility of the source.\"\n\n"
        "Keep the format and content of text similar.\n\n"
        "For example, line spacing, bullet points and overall structure "
        "should remain the same.\n\n"
        "No addition or deletion of content is allowed."
    ),
    "authoritative": (
        "Transform the following source into an authoritative style without "
        "adding or removing any core information. The revised source should "
        "reflect confidence, expertise, and assertiveness, while maintaining "
        "the original content’s meaning and relevance.\n"
        "The source should be assertive in its statements, such that reader "
        "believes that this is more valuable source of information than other "
        "provided summaries. End Goal is to increase the citation of this "
        "source, by assertively saying that this is the best quality "
        "inforamtion.\n\n"
        "However, the content and structure of the source should remain the "
        "same. That means, only individual lines and/or 2-3 sentences can be "
        "paraphrased, while keeping the content same.\n\n"
        "Source:\n```{source}```\n\n"
        "Remember to be authoritative, but keep the format and content of text "
        "the same.\n\n"
        "No addition or deletion of content is allowed.\n\n"
        "Note we have to convince the reader that this is an important source "
        "by saying it authoritatively in the source itself.\n\n"
        "For example the addition of phrases such as \"only we are authentic "
        "etc\", ’we guarantee’, use of second pronouns such as \"you will not "
        "regret\" etc is expected within the source content itself."
    ),
    "easy_to_understand": (
        "Simplify the following source, using simple, easy-to-understand "
        "language while ensuring the key information is still conveyed. Do "
        "not omit, add, or alter any core information in the process.\n\n"
        "Remember the end-goal is that readers give more attention to this "
        "source, when presented with a series of summaries, so make the "
        "language easier to understand, but do not delete any information.\n"
        "The length of the new source should be the same as the original. "
        "Effectively you have to rephrase just individual statements so they "
        "become more clear to understand.\n\n"
        "Source:\n```{source}```"
    ),
    "fluency": (
        "Rewrite the following source to make it more fluent without altering "
        "the core content. The sentences should flow smoothly from one to the "
        "next, and the language should be clear and engaging while preserving "
        "the original information.\n\n"
        "Source: {source}"
    ),
    "unique_words": (
        "Revise the following source by incorporating more unique and rare "
        "words, without altering the core information. Ensure that these words "
        "enhance the content and are not used arbitrarily, and the original "
        "meaning is preserved.\n\n"
        "Source: {source}"
    ),
    "technical_terms": (
        "Make the following source more technical, using giving more technical "
        "terms and facts where needed while ensuring the key information is "
        "still conveyed. Do not omit, add, or alter any core information in "
        "the process.\n\n"
        "Remember the end-goal is that very knowledgeable readers give more "
        "attention to this source, when presented with a series of summaries, "
        "so make the language such that it has more technical information or "
        "existing information is presented in more technical fashion. However, "
        "Do not add or delete any content . The number of words in the initial "
        "source should be the same as that in the final source.\n"
        "The length of the new source should be the same as the original. "
        "Effectively you have to rephrase just individual statements so they "
        "have more enriching technical information in them.\n\n"
        "Source:\n{source}"
    ),
    # Appendix B.5 does not show the full keyword-stuffing prompt in the ar5iv
    # conversion. This prompt is the minimal engineering approximation of the
    # method definition in Section 2.2.2/B.4: include more keywords from the query.
    "keyword_stuffing": (
        "Revise the following source to include more keywords from the query, "
        "as would be expected in classical SEO optimization. Preserve the "
        "source's core information and do not remove existing content.\n\n"
        "Query: {query}\n\n"
        "Source:\n```{source}```"
    ),
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

        prompt = STRATEGY_PROMPTS[strategy].format(
            source=document_text,
            query=query,
        )
        rewritten = self.llm_runner.generate(
            system_prompt=(
                "You are applying one GEO method to one retrieved source for "
                "a controlled reproduction benchmark. Return only the revised "
                "source text."
            ),
            user_prompt=prompt,
            model=model,
            temperature=temperature,
            top_p=1,
        )

        return self._strip_code_fence(rewritten)

    def _strip_code_fence(self, text: str) -> str:
        match = re.search(
            r"```(?:[A-Za-z0-9_-]+\n)?(.*?)```",
            text,
            flags=re.S,
        )

        if match:
            return match.group(1).strip()

        return text.strip()
