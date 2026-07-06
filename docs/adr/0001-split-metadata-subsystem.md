# Split the metadata subsystem into construction and file synchronization

Pace Downloader's metadata code handles two related but distinct responsibilities: building **Constructed Metadata** for the app to browse and resolve episodes, and performing **Media Metadata Synchronization** by writing **Managed Metadata Files** under the **Media Data Location**. We will split the implementation into a `metadata` package with explicit subsystem modules, while keeping a top-level orchestration function for the full refresh, rebuild, and sync workflow.

## Considered Options

- Keep one `metadata.py` module. This preserved simple imports but kept construction, cache management, source refresh, and disk synchronization tangled.
- Hide the split behind a classic facade. This reduced import churn but made call sites less clear about whether they were using **Constructed Metadata** or mutating files on disk.
- Use explicit subsystem namespaces under a package facade. This makes production callers use `metadata.metadata_constructor` for **Constructed Metadata**, `metadata.file_synchronizer` for **Media Metadata Synchronization**, and `metadata.refresh_build_and_sync_media()` only for the app-level workflow.

## Consequences

Production code should import `metadata` and call the relevant subsystem namespace explicitly. `service.py` is the only module that combines construction and synchronization, so workflow ordering stays centralized while individual callers remain clear about which side of the metadata subsystem they are using.
