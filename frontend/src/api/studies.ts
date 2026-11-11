import {request} from "./client";export const fetchStudies=()=>request("/studies");export const createStudies=(value:unknown)=>request("/studies","POST",value);
