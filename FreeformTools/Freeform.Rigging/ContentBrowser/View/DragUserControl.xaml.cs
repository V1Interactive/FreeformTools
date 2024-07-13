namespace Freeform.Rigging.ContentBrowser
{
    using System;
    using System.ComponentModel;
    using System.Drawing;
    using System.IO;
    using System.Windows;
    using System.Windows.Forms;
    using System.Windows.Controls;
    using System.Windows.Input;
    using System.Windows.Interop;
    using System.Windows.Media.Imaging;
    using Freeform.Core.UI;

    /// <summary>
    /// Interaction logic for DragUserControl.xaml
    /// </summary>
    public partial class DragUserControl : System.Windows.Controls.UserControl
    {
        public static readonly DependencyProperty FilePathProperty = DependencyProperty.Register("FilePath", typeof(string), typeof(DragUserControl), new UIPropertyMetadata(string.Empty));
        public static readonly DependencyProperty SelectedFileProperty = DependencyProperty.Register("SelectedFile", typeof(UserFile), typeof(DragUserControl), new UIPropertyMetadata(null));

        public string FilePath
        {
            get { return (string)GetValue(FilePathProperty); }
            set {
                SetValue(FilePathProperty, value);
            }
        }

        public UserFile SelectedFile
        {
            get { return (UserFile)GetValue(SelectedFileProperty); }
            set
            {
                SetValue(SelectedFileProperty, value);
            }
        }

        public DragUserControl()
        {
            InitializeComponent();
        }

        protected override void OnMouseMove(System.Windows.Input.MouseEventArgs e)
        {
            base.OnMouseMove(e);
            if (SelectedFile != null && 
                FilePath == SelectedFile.ItemPath && 
                e.LeftButton == MouseButtonState.Pressed && 
                System.Windows.Forms.Control.ModifierKeys != Keys.Shift && 
                System.Windows.Forms.Control.ModifierKeys != Keys.Control)
            {
                // Package the data.
                string[] files = new string[] { FilePath };
                System.Windows.DataObject dataObject = new System.Windows.DataObject(System.Windows.DataFormats.FileDrop, files);

                DragDrop.DoDragDrop(this, dataObject, System.Windows.DragDropEffects.Copy);
            }
        }

        protected override void OnMouseDoubleClick(MouseButtonEventArgs e)
        {
            base.OnMouseDoubleClick(e);
            V1DoubleClick?.Execute(DataContext);
        }

        public static readonly DependencyProperty V1DoubleClickProperty = DependencyProperty.Register( "V1DoubleClick", typeof(RelayCommand), typeof(DragUserControl), new UIPropertyMetadata(null));
        public RelayCommand V1DoubleClick
        {
            get { return (RelayCommand)GetValue(V1DoubleClickProperty); }
            set { SetValue(V1DoubleClickProperty, value); }
        }
    }
}
