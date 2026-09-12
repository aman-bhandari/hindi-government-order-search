# How the evaluation questions were written

The questions in `eval/gold.json` were written by reading the orders themselves, not generated from the
passages. That distinction decides whether the number means anything: a question generated from a passage
reuses its vocabulary, so retrieval finds it trivially and the score measures nothing.

Rules followed when writing them:

1. **Ask the way an officer would.** "Who sits on the drone committee?" not "state-level empowered committee
   constituted for drone administration".
2. **Avoid the passage's distinctive words** wherever a natural synonym exists. If the order says
   अवमुक्त (released), the question asks about funds being sanctioned.
3. **Mix languages deliberately.** Half the questions are in Hindi, half in English, and several ask in
   English about an order written only in Hindi. That is the case the multilingual embedding exists for.
4. **Include questions the corpus cannot answer.** A system that always answers is not trustworthy; these
   check that it declines.
5. **Spread across the collection**: different years, both budget and non-budget categories, and some of the
   badly scanned older orders rather than only the clean recent ones.

Recurring subjects in this department, which is what the questions draw on: SWAN (State Wide Area Network)
point-of-presence funding, the State Natural Resources Management System, Technology Vision 2020, IT Parks at
Dehradun and Bhimtal, the e-District project, the Uttarakhand Space Application Centre building, drone policy
and its committee, ICT purchase criteria, right-to-information officer designations, and annual sanctions to
UCOST and USERC.
