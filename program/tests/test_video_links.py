import tempfile
import unittest
import io
import json
from pathlib import Path
import zipfile
import importlib.util
spec = importlib.util.spec_from_file_location("video_links", Path(__file__).parents[1] / "tools/video_links.py")
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
extract_video_links, typed_ref, published_links, sync_drive_catalog = module.extract_video_links, module.typed_ref, module.published_links, module.sync_drive_catalog

HEADER = '<row r="1"><c r="A1" t="inlineStr"><is><t>{ref}</t></is></c><c r="B1" t="inlineStr"><is><t>Video</t></is></c><c r="C1" t="inlineStr"><is><t>Detay</t></is></c></row>'
def row(number, ref, value="", formula="", detail=""):
    return f'<row r="{number}"><c r="A{number}" t="inlineStr"><is><t>{ref}</t></is></c><c r="B{number}" t="inlineStr"><is><t>{value}</t></is>{formula}</c><c r="C{number}" t="inlineStr"><is><t>{detail}</t></is></c></row>'

class VideoLinksTests(unittest.TestCase):
    def workbook(self, villa, daire, links="", rels=""):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        path = Path(self.directory.name) / "portfoyler.xlsx"
        with zipfile.ZipFile(path,"w") as z:
            z.writestr("xl/workbook.xml",'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Villalar" r:id="v"/><sheet name="Daireler" r:id="d"/></sheets></workbook>')
            z.writestr("xl/_rels/workbook.xml.rels",'<Relationships><Relationship Id="v" Target="worksheets/sheet1.xml"/><Relationship Id="d" Target="worksheets/sheet2.xml"/></Relationships>')
            for i,body in enumerate([HEADER.format(ref="Foto")+villa,HEADER.format(ref="No")+daire],1):
                z.writestr(f"xl/worksheets/sheet{i}.xml",'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheetData>'+body+'</sheetData>'+ (links if i==1 else '')+'</worksheet>')
            if rels:z.writestr('xl/worksheets/_rels/sheet1.xml.rels',rels)
        return path

    def test_same_number_is_separated_and_zeroes_ignored(self):
        p=self.workbook(row(2,"villa064","https://example.com/v.mp4"),row(2,"64","https://example.com/d.mp4"))
        self.assertEqual(extract_video_links(p)['videos'],{'64v':'https://example.com/v.mp4','64d':'https://example.com/d.mp4'})
        self.assertIsNone(typed_ref('064d','v'))

    def test_blank_is_not_invented_or_substituted(self):
        self.assertEqual(extract_video_links(self.workbook(row(2,'villa64'),row(2,'64')))['videos'],{'64v':'','64d':''})

    def test_details_follow_same_type_and_number(self):
        p=self.workbook(row(2,'villa064',detail='https://example.com/v-details'),row(2,'64',detail='https://example.com/d-details'))
        self.assertEqual(extract_video_links(p)['details'],{'64v':'https://example.com/v-details','64d':'https://example.com/d-details'})

    def test_real_hyperlink_and_formula_target(self):
        p=self.workbook(row(2,'villa64','Oynat'),row(2,'64','Oynat','<f>HYPERLINK("https://example.com/d.mp4","Oynat")</f>'),'<hyperlinks><hyperlink ref="B2" r:id="link"/></hyperlinks>','<Relationships><Relationship Id="link" Target="https://example.com/v.mp4"/></Relationships>')
        self.assertEqual(extract_video_links(p)['videos']['64v'],'https://example.com/v.mp4')
        self.assertEqual(extract_video_links(p)['videos']['64d'],'https://example.com/d.mp4')

    def test_conflicting_duplicates_are_rejected(self):
        p=self.workbook(row(2,'villa64','https://example.com/a')+row(3,'villa064','https://example.com/b'),row(2,'1'))
        with self.assertRaises(ValueError):extract_video_links(p)

    def test_unsafe_url_rejected(self):
        with self.assertRaises(ValueError):extract_video_links(self.workbook(row(2,'villa64','javascript:alert(1)'),row(2,'1')))

    def test_drive_sync_updates_both_links_and_keeps_unpublished_rows_private(self):
        path=self.workbook(row(2,'villa064','https://example.com/v',detail='https://example.com/detail')+row(3,'villa65','https://example.com/unpublished'),row(2,'64','https://example.com/d'))
        data=path.read_bytes()
        class Drive:
            resource_keys={}
            def metadata(self,file_id):return {'name':'portfoyler.xlsx','id':file_id}
            def download(self,item,limit):return data
        root=Path(self.directory.name)
        (root/'program/config').mkdir(parents=True)
        (root/'program/config/catalog-source.json').write_text(json.dumps({'driveFileId':'test_catalog_id'}))
        pending={'program/config/portfolios.json':json.dumps({'villas':{'ref-064v':{'ref':'064v'}}}).encode()}
        self.assertTrue(sync_drive_catalog(Drive(),root,pending))
        result=json.loads(pending['program/config/video-links.json'])
        self.assertEqual(result['videos'],{'64v':'https://example.com/v'})
        self.assertEqual(result['details'],{'64v':'https://example.com/detail'})
        self.assertNotIn('65v',result['videos'])

    def test_disabled_catalog_leaves_existing_links_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            pending={}
            self.assertFalse(sync_drive_catalog(None,folder,pending))
            self.assertEqual(pending,{})

if __name__=='__main__':unittest.main()
