def print_weekly_summary(calendar_entries):
    target_time_in_week = 40
    weeks = {}
    sorted_entries = sorted(calendar_entries, key=lambda i: i.start)

    for entry in sorted_entries:
        week_number = entry.start.isocalendar()[1]

        if week_number not in weeks:
            weeks[week_number] = {}

        issue_id = entry.issue_id or 'UNKNOWN'
        weeks[week_number][issue_id] = entry.duration_in_hours + weeks[week_number].get(
            entry.issue_id, 0
        )

    for week, issues in weeks.items():
        print(f'Week number {week} ()')
        print('-------------------------')
        total_time_in_week = 0

        for issue_id in issues.keys():
            print('ISSUE_ID:', issue_id)
            time_spent_in_issue = issues[issue_id]
            print('TIME:', time_spent_in_issue)
            total_time_in_week = total_time_in_week + time_spent_in_issue
            print(f'{issue_id: <15} ... {time_spent_in_issue:>6} h')
        print(f'Total time in week {total_time_in_week}')
        print(f'Target time in week {target_time_in_week}')
        print(f'Balance {total_time_in_week - target_time_in_week}')
        print('')
