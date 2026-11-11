import {request} from "./client";export const fetchDatasets=()=>request("/datasets");export const createDatasets=(value:unknown)=>request("/datasets","POST",value);
