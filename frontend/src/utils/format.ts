export const fixed=(n:unknown,d=3)=>Number(n||0).toFixed(d);export const hour=(value:string)=>value.replace("T"," ").slice(0,16);
