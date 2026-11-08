# Optional reproducibility source snapshot

This folder intentionally does **not** contain source code taken from the researcher's CHTC account. To include actual user-authored runners and HTCondor batch scripts, use `../scripts/collect_source_on_chtc.sh` on `ap2001.chtc.wisc.edu`, transfer the generated `opensimad_source_snapshot.tar.gz` to Windows, inspect it for secrets and third-party license obligations, and extract into this folder before committing.

Original upstream OpenCap/OpenSimAD code, generated binaries, patient/participant datasets, `.env`, job logs and entire result archives should not be added here automatically. The snapshot scripts are specific to the archived workflow and may require the original upstream repository, compatible versions of dependencies, and correct original input bundles.
