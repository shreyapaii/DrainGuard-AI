# Licenses and Attributions

## Project code
The DrainGuard AI source code is written for this hackathon project. Add the license
you choose (for example MIT) before publishing the repository. Until then, the default
is all rights reserved.

## Libraries (core, from requirements.txt)
See the Pinned versions table in README.md for the current versions.
| Library | Version | License (verify at the project page before publishing) |
|---|---|---|
| Streamlit | 1.50.0 | Apache-2.0 |
| pandas | 2.3.3 | BSD-3-Clause |
| Plotly (Python) | 6.3.0 | MIT |
| Pillow | 11.3.0 | MIT-CMU (HPND) |
| pytest | 8.3.3 | MIT |

## Optional AI libraries (from requirements-ai.txt)
| Library | Version | License (verify at the project page before publishing) |
|---|---|---|
| PyTorch | 2.8.0 | BSD-style |
| torchvision | 0.23.0 | BSD-3-Clause |

## Model
- **Architecture and weights:** torchvision `fasterrcnn_mobilenet_v3_large_320_fpn`
  (`FasterRCNN_MobileNet_V3_Large_320_FPN_Weights.DEFAULT`), pretrained on the COCO dataset.
- **Weights are downloaded at runtime** by torchvision from the PyTorch model servers.
  No weight file is stored in this repository.
- **Weight license and COCO dataset terms:** verify on the torchvision documentation and
  the COCO dataset site (https://cocodataset.org) before any public or commercial use.
  This project has not independently verified those terms in its final form.

## Datasets and public sources
- **MCGM/BMC GIS Storm Water Drainage MapServer:** public ArcGIS REST service at
  https://prsrvgisapp.mcgm.gov.in/server/rest/services/mcgm/MCGMGIS_Departments_Master_All_Layers/MapServer.
  The service reports copyright text `MCGM, Esri India`. Imported records are stored as public
  reference infrastructure, not inspections or blockage evidence.
- **COCO (indirectly):** used only for the pretrained weights above. No COCO images are bundled.
- **TACO (https://github.com/pedropro/TACO, https://arxiv.org/abs/2003.06975,
  https://zenodo.org/records/3587843):** investigated as a candidate litter dataset. Zenodo reports
  license `cc-by-4.0`. **No TACO images or annotations are included in this project, and no model
  has been trained or fine-tuned on TACO.**
- **data.gov.in:** investigated for relevant official Indian open datasets. No records were imported.
- **Fictional demo records:** removed from the bundled operational database and no longer seeded.

## Images
Uploaded photos belong to the uploader. The app stores only the analysis summary text,
not the image file.
