from databricks.sdk import WorkspaceClient
from datetime import datetime, timezone, date

w = WorkspaceClient()

# =========================================================
# CONFIGURATION
# =========================================================

job_id = 271000619686762

# Date range
start_date = date(2026, 8, 1)
end_date   = date(2026, 8, 13)


# =========================================================
# CONVERT DATE RANGE TO TIMESTAMPS
# =========================================================

start_datetime = datetime.combine(
    start_date,
    datetime.min.time(),
    tzinfo=timezone.utc
)

end_datetime = datetime.combine(
    end_date,
    datetime.max.time(),
    tzinfo=timezone.utc
)

start_timestamp = int(
    start_datetime.timestamp() * 1000
)

end_timestamp = int(
    end_datetime.timestamp() * 1000
)


# =========================================================
# GET JOB
# =========================================================

job = w.jobs.get(
    job_id=job_id
)

print("=" * 100)
print("DATABRICKS JOB RUN TEST")
print("=" * 100)

print(f"Job ID   : {job.job_id}")
print(f"Job Name : {job.settings.name}")

print(
    f"Date Range : {start_date} to {end_date}"
)


# =========================================================
# GET RUNS
# =========================================================

try:

    runs = list(
        w.jobs.list_runs(
            job_id=job_id,
            limit=26
        )
    )

    print("\nRuns returned from API:", len(runs))

except Exception as e:

    print("ERROR:", e)

    runs = []


# =========================================================
# FILTER RUNS BY DATE
# =========================================================

filtered_runs = []

for run in runs:

    run_start = run.start_time

    if not run_start:
        continue

    if (
        start_timestamp
        <= run_start
        <= end_timestamp
    ):

        filtered_runs.append(run)


# =========================================================
# DISPLAY RESULTS
# =========================================================

print("\n" + "=" * 100)
print("FILTERED JOB RUNS")
print("=" * 100)

print(
    f"Runs found between "
    f"{start_date} and {end_date}: "
    f"{len(filtered_runs)}"
)


# =========================================================
# PROCESS RUNS
# =========================================================

success_runs = 0
failed_runs = 0


for run in filtered_runs:

    print("\n" + "-" * 100)

    print(
        f"Run ID     : {run.run_id}"
    )

    print(
        f"Run Name   : {run.run_name}"
    )

    # -----------------------------------------------------
    # Start time
    # -----------------------------------------------------

    if run.start_time:

        start_time = datetime.fromtimestamp(
            run.start_time / 1000,
            tz=timezone.utc
        )

        print(
            "Start Time :",
            start_time.strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
        )

    # -----------------------------------------------------
    # End time
    # -----------------------------------------------------

    if run.end_time:

        end_time = datetime.fromtimestamp(
            run.end_time / 1000,
            tz=timezone.utc
        )

        print(
            "End Time   :",
            end_time.strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
        )

    # -----------------------------------------------------
    # Status
    # -----------------------------------------------------

    status = "UNKNOWN"

    if run.state:

        if run.state.result_state:

            status = run.state.result_state.value

        elif run.state.life_cycle_state:

            status = run.state.life_cycle_state.value

    print(
        "Status     :",
        status
    )


    # -----------------------------------------------------
    # Count
    # -----------------------------------------------------

    if status.upper() in [
        "SUCCESS",
        "SUCCEEDED"
    ]:

        success_runs += 1

    elif status.upper() in [
        "FAILED",
        "ERROR",
        "TIMED_OUT"
    ]:

        failed_runs += 1


# =========================================================
# SUMMARY
# =========================================================

total_runs = len(
    filtered_runs
)

completed_runs = (
    success_runs +
    failed_runs
)


if completed_runs > 0:

    success_ratio = (
        success_runs /
        completed_runs
    ) * 100

else:

    success_ratio = 0


print("\n" + "=" * 100)
print("RUN SUMMARY")
print("=" * 100)

print(
    "Total Runs   :",
    total_runs
)

print(
    "Success Runs :",
    success_runs
)

print(
    "Failed Runs  :",
    failed_runs
)

print(
    "Success Ratio:",
    f"{success_ratio:.2f}%"
)