export function parseIcs(text) {
  const events = [];
  let current = null;
  const lines = text.split(/\r?\n/);

  const parseDate = (val) => {
    const m = val.match(/(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})/);
    if (!m) return null;
    const [_, y, mo, d, h, mi, s] = m;
    return new Date(
      Number(y),
      Number(mo) - 1,
      Number(d),
      Number(h),
      Number(mi),
      Number(s)
    );
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (line === "BEGIN:VEVENT") {
      current = {};
    } else if (line === "END:VEVENT") {
      if (current?.start && current?.end) {
        events.push(current);
      }
      current = null;
    } else if (current && line.includes(":")) {
      const [key, ...rest] = line.split(":");
      const value = rest.join(":");
      switch (key.toUpperCase()) {
        case "DTSTART":
          current.start = parseDate(value);
          break;
        case "DTEND":
          current.end = parseDate(value);
          break;
        case "SUMMARY":
          current.summary = value;
          break;
        case "LOCATION":
          current.location = value;
          break;
        default:
          break;
      }
    }
  }
  return events.sort((a, b) => a.start - b.start);
}

export function summarizeSchedule(events) {
  const now = new Date();
  const past = events.filter((e) => e.end <= now);
  const current = events.find((e) => e.start <= now && now < e.end);
  const future = events.filter((e) => e.start > now);

  const fmt = (e) =>
    `${e.summary} (${e.start.toLocaleString()} - ${e.end.toLocaleTimeString()})${
      e.location ? ` @ ${e.location}` : ""
    }`;

  return {
    current: current ? fmt(current) : "None",
    previous: past.slice(-2).map(fmt),
    upcoming: future.slice(0, 3).map(fmt),
  };
}
