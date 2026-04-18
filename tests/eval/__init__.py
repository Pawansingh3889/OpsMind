"""OpsMind eval harness.

Pattern borrowed from Cheuk Ting Ho's "Do you know how well your model is doing?"
tutorial (PyCon DE 2026 / PyData): task (golden set) + metric (judge) + runner.

Unlike LightEval — which targets language-model evaluation — OpsMind is an
NL-to-SQL agent, so we use pytest + custom evaluators and compare result sets
executed against the live demo database instead of scoring token likelihoods.
"""
