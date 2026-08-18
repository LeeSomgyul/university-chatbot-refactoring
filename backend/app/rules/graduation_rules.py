"""
학번별 졸업 규칙 설정
"""

GRADUATION_RULES = {
    2024: {
        'total_credits': 140,
        
        # Overflow 규칙
        'overflow': {
            # 기초 > 사고와글쓰기 OR 정량적사고 (둘 다 들으면 2학점 overflow)
            '기초_택1': {
                'type': 'course_selection',
                'codes': ['XG0701', 'XG0702'],
                'max_allowed': 1,
                'credit_per_course': 2,
                'overflow_to': '심화교양'
            },
            
            # 핵심 > 8학점 넘으면 최대 6학점까지 overflow
            '핵심': {
                'type': 'track_based',
                'track_names': ['핵심-인문학', '핵심-사회과학', '핵심-SW'],
                'base_required': 8,
                'max_overflow': 6,
                'overflow_to': '심화교양'
            },
            
            # 글로벌의사소통 > 2과목 들으면 2학점 overflow
            '글로벌의사소통': {
                'type': 'course_selection',
                'codes': ['XG0717', 'XG0718', 'XG0719'],  # 영어, 중국어, 일본어
                'max_allowed': 1,
                'credit_per_course': 2,
                'overflow_to': '심화교양'
            }
        },
        
        # 트랙 이름 매핑
        'track_names': {
            '심화교양': '심화교양',
            '기초교양': '공통교양-기초',
            '핵심교양': '핵심',
            '글로벌의사소통': '글로벌의사소통',
            '인성': '인성'
        },
        
        # 특이사항 (참고용)
        'notes': {
            'foreign_students': '순수 외국인 특별전형 입학생은 커뮤니케이션 한국어(XG0720) 필수',
            'korean_not_allowed': '일반 학생은 XG0720 수강 시 학점 미인정',
            'overflow_info': '기초 택1 초과, 핵심 8학점 초과, 글로벌 2과목 초과 시 심화교양 인정'
        }
    },
    
     2025: {
        'total_credits': 140,
        
        # Overflow 규칙 (2025학번용)
        'overflow': {
            # 2025학번은 기초교양에서 각 과목이 모두 개별 필수이므로
            # 택1 overflow가 없음
            
            # 글로벌 의사소통 > 1과목만 필수인데 2과목 들으면 overflow
            # (2024와 동일한 규칙 - 과목 코드는 동일하다고 가정)
            '글로벌의사소통': {
                'type': 'course_selection',
                'codes': ['XG0717', 'XG0718', 'XG0719'],  # 영어, 중국어, 일본어
                'max_allowed': 1,
                'credit_per_course': 2,
                'overflow_to': '창의교양'
            },
            
            # 핵심교양 > 6학점 필수인데 초과하면 overflow 가능
            # (필요시 추가 - 현재는 명확한 규칙이 없으므로 생략)
            # '핵심교양': {
            #     'type': 'track_based',
            #     'track_names': ['핵심교양-문학예술', '핵심교양-역사철학', '핵심교양-사회문화'],
            #     'base_required': 6,
            #     'max_overflow': 4,
            #     'overflow_to': '창의교양'
            # }
        },
        
        # 트랙 이름 매핑 (2025학번)
        'track_names': {
            '심화교양': '창의교양',      # 2025는 창의교양으로 명명
            '기초교양': '기초교양',       # 동일
            '핵심교양': '핵심교양',       # 동일
            '창의교양': '창의교양',       # 새로운 분류
            '글로벌의사소통': '글로벌 의사소통',
            '인성': '향림인성',
            '미래설계': '미래설계',
            '학문기초': '학문기초',
            '자유선택': '자유선택'
        },
        
        'notes': {
            'foreign_students': '순수 외국인 특별전형 입학생은 커뮤니케이션 한국어 필수',
            'graduation_requirements': '교양 30학점(기초 10 + 핵심 6 + 창의 14), 전공 70학점(전필 36 + 전선 34)',
            'liberal_arts_max': '교양은 최대 46학점까지 인정'
        }
    }
}


def get_rules(admission_year: int) -> dict:
    """
    학번별 규칙 가져오기
    
    Args:
        admission_year: 입학년도
        
    Returns:
        해당 학번의 규칙 dict
    """
    if admission_year in GRADUATION_RULES:
        return GRADUATION_RULES[admission_year]
    
    # 기본값 (2024학번 규칙 사용)
    print(f"⚠️ {admission_year}학번 규칙이 없어 2024학번 규칙을 사용합니다.")
    return GRADUATION_RULES[2024]


def get_overflow_target_key(admission_year: int) -> str:
    """
    Overflow가 인정되는 목표 트랙 이름
    (대부분 심화교양/창의교양)
    """
    rules = get_rules(admission_year)
    track_names = rules.get('track_names', {})
    return track_names.get('심화교양', '심화교양')