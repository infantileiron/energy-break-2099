export type Role="admin"|"analyst"|"viewer";
export interface User{email:string;role:Role}
export interface Entity{id:string;created_at:string;[key:string]:any}
export interface Observation{timestamp:string;kwh:number;output_kg:number;intensity:number;score:number;baseline:number;anomaly:boolean}
export interface Segment{start_index:number;end_index:number;count:number;mean:number;sse:number;start_at:string;end_at:string}
