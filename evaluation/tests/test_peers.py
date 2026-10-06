from evaluation.peers import select_revision


def test_file_revision_time_beats_branch_tip_time():
    selected=select_revision([
        {'ref':'origin/agent-1','changeTime':100,'changeCommit':'1','sha256':'old','branchTipTime':500},
        {'ref':'origin/agent-3','changeTime':200,'changeCommit':'2','sha256':'new','branchTipTime':250},
    ])
    assert selected['sha256']=='new' and not selected['ambiguous']


def test_equal_time_conflicting_contents_are_flagged_not_silently_trusted():
    selected=select_revision([
        {'ref':'origin/agent-1','changeTime':200,'changeCommit':'1','sha256':'a'},
        {'ref':'origin/agent-3','changeTime':200,'changeCommit':'2','sha256':'b'},
    ])
    assert selected['ambiguous']
