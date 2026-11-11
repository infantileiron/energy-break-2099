export const roles=["admin","analyst","viewer"] as const;
export const runStatuses=["queued","running","completed","failed"] as const;
export const meterStatuses=["running","stopped"] as const;
export const exclusionLabels:Record<string,string>={stopped:"停机",zero_output:"零产量",missing_measurement:"缺测"};
