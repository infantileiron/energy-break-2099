import {request} from "./client";export const fetchRuns=()=>request("/runs");export const createRuns=(value:unknown)=>request("/runs","POST",value);
