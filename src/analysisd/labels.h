/*
 * Label data cache
 * Copyright (C) 2015-2020, Wazuh Inc.
 * February 27, 2017.
 *
 * This program is free software; you can redistribute it
 * and/or modify it under the terms of the GNU General Public
 * License (version 2) as published by the FSF - Free Software
 * Foundation.
 */

#ifndef LABELS_H
#define LABELS_H

typedef struct wlabel_data_t {
    wlabel_t *labels;
    time_t mtime;
    unsigned int error_flag;
} wlabel_data_t;

/* Initialize label cache */
int labels_init();

/**
 * @brief Finds the label array of an agent that generated an event.
 * 
 * @param lf The Eventinfo data structure.
 * @retval The agent's labels array on success. NULL on error.
 */
wlabel_t* labels_find(const Eventinfo *lf);

#endif
