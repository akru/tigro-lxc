# -*- coding: utf-8 -*- 
## @package dictdiffer
#  Dictionary difference calculator package.
#
#  (c) hughdbrown from stackoverflow.com


## Dictionary match class
#
#  Calculate the difference between two dictionaries as:
#  (1) items added
#  (2) items removed
#  (3) keys same in both but changed values
#  
class DictDiffer:

    ## The constructor
    #  @param current_dict The current dictionary for matching.
    #  @param past_dict The old dictionary for matching.
    def __init__(s, current_dict, past_dict):

        # Save dictionaries on self
        s.current_dict, s.past_dict = current_dict, past_dict

        # Save dictionaries sets on self
        s.set_current, s.set_past = set(current_dict.keys()), set(past_dict.keys())

        # Save current dictionary intersection on self
        s.intersect = s.set_current.intersection(s.set_past)

    ## Items added calculate method
    @property
    def added(s):

        # Find added items
        added_set = s.set_current - s.intersect 

        # Return dict of added items
        return { i : s.current_dict[i] for i in added_set }

    ## Items removed calculate method
    @property
    def removed(s):

        # Find removed items
        removed_set = s.set_past - s.intersect

        # Return dict of removed items
        return { i : s.past_dict[i] for i in removed_set }

    ## Items changed calculate method
    @property
    def changed(s):

        # Find changed items
        changed_set = set(o for o in s.intersect if s.past_dict[o] != s.current_dict[o]) 

        # Return dict of changed items (before, after)
        return (
            { i : s.past_dict[i] for i in changed_set },
            { i : s.current_dict[i] for i in changed_set }
        )
