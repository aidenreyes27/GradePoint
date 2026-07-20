/**
 * GradePoint academic record — localStorage model + GPA helpers.
 * Data stays in the browser so a 4-year plan fits without a database.
 */
(function (global) {
  const STORAGE_KEY = "gradepoint-record-v1";

  const GRADE_POINTS = {
    A: 4.0,
    "A-": 3.7,
    "B+": 3.3,
    B: 3.0,
    "B-": 2.7,
    "C+": 2.3,
    C: 2.0,
    "C-": 1.7,
    "D+": 1.3,
    D: 1.0,
    "D-": 0.7,
    F: 0.0,
  };

  const GRADE_ORDER = Object.keys(GRADE_POINTS);

  function uid(prefix) {
    return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
  }

  function defaultRecord() {
    const seasons = ["Fall", "Spring"];
    const years = [];
    for (let y = 1; y <= 4; y++) {
      const terms = seasons.map((season) => ({
        id: uid(`y${y}-${season.toLowerCase()}`),
        name: `${season} · Year ${y}`,
        season,
        year: y,
        classes: [],
      }));
      years.push({ label: `Year ${y}`, year: y, terms });
    }
    return {
      version: 1,
      studentName: "",
      schoolName: "",
      major: "",
      goal: { targetGpa: 3.5, note: "" },
      years,
      activeTermId: years[0].terms[0].id,
    };
  }

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultRecord();
      const data = JSON.parse(raw);
      if (!data.years || !Array.isArray(data.years)) return defaultRecord();
      return data;
    } catch {
      return defaultRecord();
    }
  }

  function save(record) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
    global.dispatchEvent(new CustomEvent("gradepoint:save", { detail: record }));
  }

  function reset() {
    const fresh = defaultRecord();
    save(fresh);
    return fresh;
  }

  function allTerms(record) {
    const terms = [];
    for (const year of record.years || []) {
      for (const term of year.terms || []) {
        terms.push(term);
      }
    }
    return terms;
  }

  function findTerm(record, termId) {
    return allTerms(record).find((t) => t.id === termId) || null;
  }

  function activeTerm(record) {
    let term = findTerm(record, record.activeTermId);
    if (!term) {
      term = allTerms(record)[0] || null;
      if (term) record.activeTermId = term.id;
    }
    return term;
  }

  function gradedClasses(classes) {
    return (classes || []).filter(
      (c) => c.grade && GRADE_POINTS[String(c.grade).toUpperCase()] !== undefined
    );
  }

  function calculateTermGpa(classes) {
    const graded = gradedClasses(classes);
    let units = 0;
    let qp = 0;
    for (const c of graded) {
      const u = Number(c.units) || 0;
      const g = GRADE_POINTS[String(c.grade).toUpperCase()];
      units += u;
      qp += g * u;
    }
    return {
      gpa: units ? qp / units : 0,
      units,
      qualityPoints: qp,
      gradedCount: graded.length,
    };
  }

  function analyze(record) {
    const history = [];
    let runUnits = 0;
    let runQp = 0;

    for (const term of allTerms(record)) {
      const { gpa, units, qualityPoints, gradedCount } = calculateTermGpa(term.classes);
      if (gradedCount === 0) continue;
      runUnits += units;
      runQp += qualityPoints;
      history.push({
        id: term.id,
        name: term.name,
        season: term.season,
        year: term.year,
        termGpa: gpa,
        units,
        cumulativeGpa: runQp / runUnits,
        classCount: gradedCount,
      });
    }

    return {
      history,
      cumulativeGpa: runUnits ? runQp / runUnits : null,
      totalUnits: runUnits,
      totalQualityPoints: runQp,
    };
  }

  function plannedUnits(record) {
    let units = 0;
    let count = 0;
    for (const term of allTerms(record)) {
      for (const c of term.classes || []) {
        units += Number(c.units) || 0;
        count += 1;
      }
    }
    return { units, count };
  }

  function goalStatus(record) {
    const target = Number(record.goal?.targetGpa);
    const { cumulativeGpa, totalUnits } = analyze(record);
    if (!Number.isFinite(target)) {
      return { status: "unset", message: "Set a target GPA to track progress." };
    }
    if (cumulativeGpa == null || totalUnits <= 0) {
      return {
        status: "no_data",
        target,
        current: null,
        delta: null,
        message: "Add graded courses to start tracking your goal.",
      };
    }
    const delta = cumulativeGpa - target;
    if (Math.abs(delta) < 0.005) {
      return {
        status: "met",
        target,
        current: cumulativeGpa,
        delta,
        message: "You are right on your goal GPA.",
      };
    }
    if (delta > 0) {
      return {
        status: "ahead",
        target,
        current: cumulativeGpa,
        delta,
        message: `You are ${delta.toFixed(2)} points above your goal.`,
      };
    }
    return {
      status: "behind",
      target,
      current: cumulativeGpa,
      delta,
      message: `You are ${Math.abs(delta).toFixed(2)} points below your goal.`,
    };
  }

  function requiredTermGpa(priorUnits, priorGpa, termUnits, target) {
    const total = priorUnits + termUnits;
    if (termUnits <= 0 || total <= 0) return null;
    return (target * total - priorGpa * priorUnits) / termUnits;
  }

  function formatGpa(n) {
    if (n == null || Number.isNaN(n)) return "—";
    return Number(n).toFixed(2);
  }

  function exportJson(record) {
    return JSON.stringify(record, null, 2);
  }

  function importJson(text) {
    const data = JSON.parse(text);
    if (!data.years) throw new Error("Invalid GradePoint export.");
    save(data);
    return data;
  }

  global.GradePointRecord = {
    STORAGE_KEY,
    GRADE_POINTS,
    GRADE_ORDER,
    uid,
    defaultRecord,
    load,
    save,
    reset,
    allTerms,
    findTerm,
    activeTerm,
    gradedClasses,
    calculateTermGpa,
    analyze,
    plannedUnits,
    goalStatus,
    requiredTermGpa,
    formatGpa,
    exportJson,
    importJson,
  };
})(window);
