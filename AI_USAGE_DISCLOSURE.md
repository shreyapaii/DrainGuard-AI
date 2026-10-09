# AI Usage Disclosure

**Tools used to build this project:** AI coding assistants were used in chat conversations to
generate, review, and revise source code, documentation, tests, and data-source notes.

**What the AI produced:** the application code, tests, configuration, and this documentation
drafts. The team reviewed and ran the code and tests.

**What the project uses at runtime:**
- A pretrained COCO object detector (torchvision Faster R-CNN, MobileNetV3) runs on the user's
  computer or server to analyse uploaded images. This is real inference, not simulated output.
- The detector is a general-purpose model. It is not trained or validated for drain blockage
  or litter-specific detection, and the app says so in its interface.
- The priority score is a rule-based calculation, not a machine-learning prediction.
- Public infrastructure imports are stored separately from inspections. They are not AI output
  and do not imply blockage, inspection, maintenance status, or flood risk.

**What the project does not claim:**
- No model accuracy, precision, or recall has been measured for this use case.
- No field trial, municipal deployment, or flood-prediction validation has taken place.
- Real public MCGM/BMC stormwater infrastructure records are imported as reference infrastructure
  only. They are Mumbai records and must not be represented as Belagavi inspections or conditions.

**Team responsibility:** the team is responsible for checking the code, licenses, and
claims before submission.
