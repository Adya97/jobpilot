---
name: apply-approved
description: Submit applications the user approved on the dashboard (status approved) by filling the job's application form in Chrome. Use for "apply", "submit approved jobs", or the scheduled submit run.
---

# Submit approved applications

Never submit a job whose status is not `approved`. Stop after 15 submissions per day: check `python3 scripts/jobs.py stats` and the dashboard's "Applied today" count.

1. List jobs: `python3 scripts/jobs.py list --status approved`.
2. Load the claude-in-chrome skill. For each job, one at a time:
   a. Open `apply_url` in a new tab. Take a screenshot.
   b. Fill fields from `profile/master_profile.yaml` (name, email, phone, location, LinkedIn, GitHub, portfolio)
      and `profile/answer_bank.yaml` (work permit, sponsorship = No, salary, notice period, start date,
      relocation, languages, gender, disability).
   c. Upload `output/applications/<slug>/<First>_<Last>_CV.pdf`, and `<First>_<Last>_Cover_Letter.pdf` where there is a cover letter field.
      Paste the cover letter text into a text box when no upload is offered.
   d. Answer "why us" and "why this role" from the job's `answers`. For any other free-text question, write
      2–3 sentences using only facts from the master profile.
   e. **Stop and ask the user** on a CAPTCHA, a login wall, an account-creation step, an assessment or test,
      a question the profile can't answer truthfully, or a required field you aren't sure about. Leave the tab
      open and move to the next job.
   f. Take a screenshot of the completed form and save it to `output/applications/<slug>/form.png`. Then submit,
      and take a screenshot of the confirmation page saved to `confirmation.png`.
   g. Record the result:
      `python3 scripts/jobs.py applied '<id>'`
      This sets status `applied`, `applied_at` to now and `followup_due` to 7 days later.
3. LinkedIn jobs (`source = linkedin`):
   - `easy_apply = 1`: open the job URL, click "Easy Apply" and go through the steps. Contact details come
     from the LinkedIn profile: check they match the master profile. Upload `<First>_<Last>_CV.pdf` when asked
     (choose upload, not a stored resume). Answer screening questions from the answer bank. Years of experience
     with a specific tool means whole years from the profile, and 0 if the tool is not there. German level is
     B1, so for "Do you speak German fluently?" answer No. Uncheck "Follow company" before the final Submit.
   - `easy_apply = 0`: click "Apply", which opens the company's own site. Fill that form as in step 2.
   - Wait 60–120 s between LinkedIn submissions and never do more than 5 in a row.
     Stop at once on any CAPTCHA, "unusual activity" warning or rate-limit notice, and tell the user.
   - Collect fresh top-pick ids by visiting https://www.linkedin.com/jobs/collections/recommended/ and saving the
     job ids to `data/linkedin_top_picks.txt` (comma-separated). Discovery reads them through the guest API.
4. Report: submitted, waiting on the user (with the reason), and skipped.

## Upload buttons with no file input
Some forms create the `<input type=file>` only when the button is clicked, which opens a native picker Claude
cannot use. Run this with javascript_tool first:
`HTMLInputElement.prototype.click` patched so that, for `type=file`, it appends the input to `document.body`,
sets `data-jp-captured`, and returns without opening the picker. Then trigger the page's upload button with
JS `.click()`, `find` the captured input and use `file_upload` on it.

## Accounts and logins
If a site requires creating an account or logging in before applying, do not create one. Set the status
`needs_user` with the URL in the note (`python3 scripts/jobs.py status '<id>' needs_user '<url>'`) and move on.

## Enumerate every field type, including sliders
List ALL `input` elements with no type filter: range sliders, date, number, and hidden-styled custom widgets.
On 2026-10-21 an ATU salary slider (`type=range`, monthly gross) was missed and submitted at its default of
1,000 EUR. For a range input, set it with the native value setter plus `input` and `change` events, then read back
the displayed value. Monthly salary is `salary_expectation_monthly_gross_eur` in the answer bank.

## Radios and checkboxes: select by label text, then verify
Element refs and coordinates go stale when the page shifts (e.g. after a file upload). Select options with
javascript_tool by matching the label text and calling `label.click()`. Before submitting, always read back
every checked input's label and every text value, and compare them with the intended answers. On 2026-10-21
a stale click ticked "based in Berlin" and "EU citizen". The read-back caught it before submit.

## SmartRecruiters (oneclick-ui): fields in shadow DOM
`find` and `read_page` can't see these inputs. Fill text inputs with javascript_tool: walk the shadow roots, use the
native value setter, then dispatch `input`, `change` and `blur` with `{bubbles:true, composed:true}`. For the resume
`input[type=file]`, move it to `document.body`, `find` it, run `file_upload`, then move it back to its parent.
Click and type for autocomplete fields (City) and for the screening page. Paste the cover letter into
"Message to the Hiring Team" when there is no cover letter upload.
